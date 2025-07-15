"""
告警管理器
负责监控交易系统状态，触发和管理告警
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging
from dataclasses import dataclass, asdict

from core.config_manager import ConfigManager
from core.logger import LoggerManager


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误
    CRITICAL = "critical"   # 严重


@dataclass
class Alert:
    """告警对象"""
    id: str                          # 告警ID
    title: str                       # 告警标题
    message: str                     # 告警消息
    level: AlertLevel                # 告警级别
    source: str                      # 告警源
    timestamp: datetime              # 告警时间
    data: Dict[str, Any]            # 相关数据
    acknowledged: bool = False       # 是否已确认
    resolved: bool = False          # 是否已解决
    resolution_time: Optional[datetime] = None  # 解决时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['level'] = self.level.value
        if self.resolution_time:
            result['resolution_time'] = self.resolution_time.isoformat()
        return result


@dataclass 
class AlertRule:
    """告警规则"""
    id: str                          # 规则ID
    name: str                        # 规则名称
    condition: str                   # 触发条件
    level: AlertLevel                # 告警级别
    message_template: str            # 消息模板
    enabled: bool = True             # 是否启用
    cooldown: int = 300              # 冷却时间（秒）
    last_triggered: Optional[datetime] = None  # 上次触发时间


class AlertManager:
    """
    告警管理器
    负责监控系统状态、触发告警、发送通知
    """
    
    def __init__(self, config_manager: ConfigManager, logger_manager: LoggerManager):
        """
        初始化告警管理器
        
        Args:
            config_manager: 配置管理器
            logger_manager: 日志管理器
        """
        self.config_manager = config_manager
        self.logger_manager = logger_manager
        self.logger = logger_manager.get_logger('alert_manager')
        
        # 告警存储
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.ERROR: [],
            AlertLevel.CRITICAL: []
        }
        
        # 配置
        self.max_alerts = config_manager.get('monitoring.alerts.max_alerts', 1000)
        self.alert_retention_days = config_manager.get('monitoring.alerts.retention_days', 30)
        self.notification_enabled = config_manager.get('monitoring.alerts.notifications.enabled', True)
        
        # 统计信息
        self.stats = {
            'total_alerts': 0,
            'alerts_by_level': {level.value: 0 for level in AlertLevel},
            'alerts_acknowledged': 0,
            'alerts_resolved': 0
        }
        
        # 加载默认规则
        self._load_default_rules()
        
        # 启动后台任务
        self.running = False
        self.background_task = None
        
        self.logger.info("告警管理器初始化完成")
    
    def _load_default_rules(self):
        """加载默认告警规则"""
        default_rules = [
            AlertRule(
                id="position_loss",
                name="持仓亏损告警",
                condition="position_loss_percent > 5",
                level=AlertLevel.WARNING,
                message_template="持仓亏损超过 {loss_percent}%"
            ),
            AlertRule(
                id="position_major_loss", 
                name="持仓重大亏损告警",
                condition="position_loss_percent > 10",
                level=AlertLevel.CRITICAL,
                message_template="持仓重大亏损 {loss_percent}%，需要立即关注"
            ),
            AlertRule(
                id="api_connection_error",
                name="API连接错误",
                condition="api_connection_failed",
                level=AlertLevel.ERROR,
                message_template="API连接失败: {error_message}"
            ),
            AlertRule(
                id="insufficient_balance",
                name="余额不足告警",
                condition="available_balance < min_balance",
                level=AlertLevel.WARNING,
                message_template="可用余额不足: {available_balance}"
            ),
            AlertRule(
                id="strategy_error",
                name="策略执行错误",
                condition="strategy_execution_failed",
                level=AlertLevel.ERROR,
                message_template="策略 {strategy_name} 执行失败: {error_message}"
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
        
        self.logger.info(f"加载了 {len(default_rules)} 个默认告警规则")
    
    def add_rule(self, rule: AlertRule):
        """
        添加告警规则
        
        Args:
            rule: 告警规则
        """
        self.alert_rules[rule.id] = rule
        self.logger.info(f"添加告警规则: {rule.name}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        移除告警规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功移除
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"移除告警规则: {rule_id}")
            return True
        return False
    
    def add_handler(self, level: AlertLevel, handler: Callable[[Alert], None]):
        """
        添加告警处理器
        
        Args:
            level: 告警级别
            handler: 处理器函数
        """
        self.alert_handlers[level].append(handler)
        self.logger.info(f"为 {level.value} 级别添加告警处理器")
    
    async def trigger_alert(
        self, 
        rule_id: str, 
        title: str,
        message: str, 
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
        level: Optional[AlertLevel] = None
    ) -> Optional[Alert]:
        """
        触发告警
        
        Args:
            rule_id: 规则ID
            title: 告警标题
            message: 告警消息
            source: 告警源
            data: 相关数据
            level: 告警级别（可选，从规则获取）
            
        Returns:
            Optional[Alert]: 生成的告警对象
        """
        # 检查规则
        rule = self.alert_rules.get(rule_id)
        if not rule or not rule.enabled:
            return None
        
        # 检查冷却时间
        if rule.last_triggered:
            time_since_last = datetime.now() - rule.last_triggered
            if time_since_last.total_seconds() < rule.cooldown:
                return None
        
        # 使用规则级别或指定级别
        alert_level = level or rule.level
        
        # 创建告警
        alert_id = f"{rule_id}_{int(datetime.now().timestamp())}"
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            level=alert_level,
            source=source,
            timestamp=datetime.now(),
            data=data or {}
        )
        
        # 存储告警
        self.alerts[alert_id] = alert
        
        # 更新规则触发时间
        rule.last_triggered = datetime.now()
        
        # 更新统计
        self.stats['total_alerts'] += 1
        self.stats['alerts_by_level'][alert_level.value] += 1
        
        # 清理旧告警
        await self._cleanup_old_alerts()
        
        # 发送通知
        await self._send_notifications(alert)
        
        self.logger.info(f"触发告警 [{alert_level.value}]: {title}")
        
        return alert
    
    async def acknowledge_alert(self, alert_id: str, acknowledger: str = "system") -> bool:
        """
        确认告警
        
        Args:
            alert_id: 告警ID
            acknowledger: 确认人
            
        Returns:
            bool: 是否成功确认
        """
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.acknowledged = True
            alert.data['acknowledger'] = acknowledger
            alert.data['acknowledge_time'] = datetime.now().isoformat()
            
            self.stats['alerts_acknowledged'] += 1
            
            self.logger.info(f"告警已确认: {alert_id} by {acknowledger}")
            return True
        
        return False
    
    async def resolve_alert(self, alert_id: str, resolver: str = "system") -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警ID
            resolver: 解决人
            
        Returns:
            bool: 是否成功解决
        """
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = datetime.now()
            alert.data['resolver'] = resolver
            
            self.stats['alerts_resolved'] += 1
            
            self.logger.info(f"告警已解决: {alert_id} by {resolver}")
            return True
        
        return False
    
    async def _send_notifications(self, alert: Alert):
        """
        发送告警通知
        
        Args:
            alert: 告警对象
        """
        if not self.notification_enabled:
            return
        
        # 调用注册的处理器
        handlers = self.alert_handlers.get(alert.level, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"告警处理器执行失败: {e}")
    
    async def _cleanup_old_alerts(self):
        """清理过期告警"""
        if len(self.alerts) <= self.max_alerts:
            return
        
        # 按时间排序，删除最旧的告警
        sorted_alerts = sorted(
            self.alerts.items(),
            key=lambda x: x[1].timestamp
        )
        
        # 保留最新的告警
        alerts_to_keep = dict(sorted_alerts[-self.max_alerts:])
        removed_count = len(self.alerts) - len(alerts_to_keep)
        
        self.alerts = alerts_to_keep
        
        if removed_count > 0:
            self.logger.info(f"清理了 {removed_count} 个旧告警")
    
    def get_alerts(
        self, 
        level: Optional[AlertLevel] = None,
        source: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        获取告警列表
        
        Args:
            level: 过滤告警级别
            source: 过滤告警源
            resolved: 过滤是否已解决
            limit: 限制数量
            
        Returns:
            List[Alert]: 告警列表
        """
        alerts = list(self.alerts.values())
        
        # 过滤
        if level:
            alerts = [a for a in alerts if a.level == level]
        if source:
            alerts = [a for a in alerts if a.source == source]
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        # 按时间倒序排序
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取告警统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'active_alerts': len([a for a in self.alerts.values() if not a.resolved]),
            'rules_count': len(self.alert_rules),
            'handlers_count': sum(len(handlers) for handlers in self.alert_handlers.values())
        }
    
    async def start(self):
        """启动告警管理器"""
        if self.running:
            return
        
        self.running = True
        self.background_task = asyncio.create_task(self._background_monitor())
        
        self.logger.info("告警管理器已启动")
    
    async def stop(self):
        """停止告警管理器"""
        if not self.running:
            return
        
        self.running = False
        
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("告警管理器已停止")
    
    async def _background_monitor(self):
        """后台监控任务"""
        while self.running:
            try:
                # 定期清理过期告警
                await self._cleanup_old_alerts()
                
                # 等待30秒
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"后台监控任务错误: {e}")
                await asyncio.sleep(60)  # 出错后等待更长时间


def create_alert_manager(config_manager: ConfigManager, logger_manager: LoggerManager) -> AlertManager:
    """
    创建告警管理器实例
    
    Args:
        config_manager: 配置管理器
        logger_manager: 日志管理器
        
    Returns:
        AlertManager: 告警管理器实例
    """
    return AlertManager(config_manager, logger_manager)