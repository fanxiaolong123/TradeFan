"""
TradeFan 全栈监控体系
支持 Prometheus + Grafana 监控架构

监控架构:
应用监控 → 指标收集 → 数据存储 → 可视化 → 告警
"""

import asyncio
import logging
import time
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import json

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Install with: pip install prometheus-client")


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """告警对象"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    created_time: datetime
    resolved_time: Optional[datetime] = None
    acknowledged_time: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        
        if PROMETHEUS_AVAILABLE:
            self._initialize_metrics()
    
    def _initialize_metrics(self):
        """初始化Prometheus指标"""
        # 业务指标
        self.orders_total = Counter(
            'trading_orders_total', 
            'Total number of orders',
            ['status', 'symbol', 'strategy'],
            registry=self.registry
        )
        
        self.order_latency = Histogram(
            'trading_order_latency_seconds',
            'Order execution latency',
            ['symbol', 'order_type'],
            registry=self.registry
        )
        
        self.pnl_gauge = Gauge(
            'trading_pnl',
            'Current P&L',
            ['strategy', 'symbol'],
            registry=self.registry
        )
        
        self.positions_gauge = Gauge(
            'trading_positions',
            'Current positions',
            ['symbol'],
            registry=self.registry
        )
        
        self.trade_volume = Counter(
            'trading_volume_total',
            'Total trading volume',
            ['symbol', 'side'],
            registry=self.registry
        )
        
        # 系统指标
        self.cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.network_io = Counter(
            'system_network_io_bytes_total',
            'Network IO bytes',
            ['direction'],
            registry=self.registry
        )
        
        self.disk_io = Counter(
            'system_disk_io_bytes_total',
            'Disk IO bytes',
            ['direction'],
            registry=self.registry
        )
        
        # 应用指标
        self.api_requests = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.api_latency = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.websocket_connections = Gauge(
            'websocket_connections_active',
            'Active WebSocket connections',
            ['exchange'],
            registry=self.registry
        )
        
        self.data_points_processed = Counter(
            'data_points_processed_total',
            'Total data points processed',
            ['source', 'type'],
            registry=self.registry
        )
    
    def record_order(self, status: str, symbol: str, strategy: str = "default"):
        """记录订单指标"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'orders_total'):
            self.orders_total.labels(status=status, symbol=symbol, strategy=strategy).inc()
    
    def record_order_latency(self, latency_seconds: float, symbol: str, order_type: str):
        """记录订单延迟"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'order_latency'):
            self.order_latency.labels(symbol=symbol, order_type=order_type).observe(latency_seconds)
    
    def update_pnl(self, pnl: float, strategy: str, symbol: str):
        """更新损益指标"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'pnl_gauge'):
            self.pnl_gauge.labels(strategy=strategy, symbol=symbol).set(pnl)
    
    def update_position(self, position: float, symbol: str):
        """更新仓位指标"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'positions_gauge'):
            self.positions_gauge.labels(symbol=symbol).set(position)
    
    def record_trade_volume(self, volume: float, symbol: str, side: str):
        """记录交易量"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'trade_volume'):
            self.trade_volume.labels(symbol=symbol, side=side).inc(volume)
    
    def update_system_metrics(self):
        """更新系统指标"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_percent)
            
            # 内存使用
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.used)
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.network_io.labels(direction='sent').inc(net_io.bytes_sent)
            self.network_io.labels(direction='recv').inc(net_io.bytes_recv)
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.disk_io.labels(direction='read').inc(disk_io.read_bytes)
                self.disk_io.labels(direction='write').inc(disk_io.write_bytes)
                
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
    
    def record_api_request(self, method: str, endpoint: str, status: str, duration: float):
        """记录API请求"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.api_requests.labels(method=method, endpoint=endpoint, status=status).inc()
        self.api_latency.labels(method=method, endpoint=endpoint).observe(duration)
    
    def update_websocket_connections(self, count: int, exchange: str):
        """更新WebSocket连接数"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'websocket_connections'):
            self.websocket_connections.labels(exchange=exchange).set(count)
    
    def record_data_point(self, source: str, data_type: str, count: int = 1):
        """记录数据点处理"""
        if PROMETHEUS_AVAILABLE and hasattr(self, 'data_points_processed'):
            self.data_points_processed.labels(source=source, type=data_type).inc(count)


class AlertRule:
    """告警规则"""
    
    def __init__(self, name: str, condition: Callable[[], bool], 
                 severity: AlertSeverity, description: str = ""):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.description = description
        self.last_check = None
        self.is_active = False


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        # 默认告警规则
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        # CPU使用率告警
        self.add_alert_rule(
            "high_cpu_usage",
            lambda: psutil.cpu_percent() > 80,
            AlertSeverity.WARNING,
            "CPU usage is above 80%"
        )
        
        # 内存使用率告警
        self.add_alert_rule(
            "high_memory_usage",
            lambda: psutil.virtual_memory().percent > 85,
            AlertSeverity.WARNING,
            "Memory usage is above 85%"
        )
        
        # 磁盘空间告警
        self.add_alert_rule(
            "low_disk_space",
            lambda: psutil.disk_usage('/').percent > 90,
            AlertSeverity.CRITICAL,
            "Disk usage is above 90%"
        )
    
    def add_alert_rule(self, name: str, condition: Callable[[], bool],
                      severity: AlertSeverity, description: str = ""):
        """添加告警规则"""
        rule = AlertRule(name, condition, severity, description)
        self.alert_rules[name] = rule
        self.logger.info(f"Added alert rule: {name}")
    
    def add_notification_channel(self, name: str, callback: Callable[[Alert], None]):
        """添加通知渠道"""
        self.notification_channels[name] = callback
        self.logger.info(f"Added notification channel: {name}")
    
    async def check_alerts(self):
        """检查所有告警规则"""
        for rule_name, rule in self.alert_rules.items():
            try:
                # 检查条件
                is_triggered = rule.condition()
                current_time = datetime.now(timezone.utc)
                
                if is_triggered and not rule.is_active:
                    # 触发新告警
                    alert = Alert(
                        id=f"{rule_name}_{int(time.time())}",
                        name=rule_name,
                        description=rule.description,
                        severity=rule.severity,
                        status=AlertStatus.ACTIVE,
                        created_time=current_time
                    )
                    
                    self.active_alerts[alert.id] = alert
                    self.alert_history.append(alert)
                    rule.is_active = True
                    
                    # 发送通知
                    await self._send_notifications(alert)
                    
                    self.logger.warning(f"Alert triggered: {rule_name}")
                
                elif not is_triggered and rule.is_active:
                    # 解决告警
                    for alert_id, alert in list(self.active_alerts.items()):
                        if alert.name == rule_name:
                            alert.status = AlertStatus.RESOLVED
                            alert.resolved_time = current_time
                            del self.active_alerts[alert_id]
                            
                            await self._send_notifications(alert)
                            self.logger.info(f"Alert resolved: {rule_name}")
                    
                    rule.is_active = False
                
                rule.last_check = current_time
                
            except Exception as e:
                self.logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """发送告警通知"""
        for channel_name, callback in self.notification_channels.items():
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Error sending notification via {channel_name}: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_time = datetime.now(timezone.utc)
            self.logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        severity_counts = {}
        for alert in self.alert_history:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "severity_distribution": severity_counts,
            "alert_rules": len(self.alert_rules)
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
    
    def start_timer(self, name: str) -> str:
        """开始计时"""
        timer_id = f"{name}_{int(time.time() * 1000000)}"
        self.metrics[timer_id] = {
            "name": name,
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
        return timer_id
    
    def end_timer(self, timer_id: str) -> Optional[float]:
        """结束计时"""
        if timer_id not in self.metrics:
            return None
        
        end_time = time.time()
        self.metrics[timer_id]["end_time"] = end_time
        duration = end_time - self.metrics[timer_id]["start_time"]
        self.metrics[timer_id]["duration"] = duration
        
        return duration
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标"""
        metric_id = f"{name}_{int(time.time() * 1000000)}"
        self.metrics[metric_id] = {
            "name": name,
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {}
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        uptime = time.time() - self.start_time
        
        # 计算各种统计
        timer_metrics = [m for m in self.metrics.values() if "duration" in m and m["duration"]]
        
        if timer_metrics:
            durations = [m["duration"] for m in timer_metrics]
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = max_duration = min_duration = 0
        
        return {
            "uptime_seconds": uptime,
            "total_metrics": len(self.metrics),
            "timer_metrics": len(timer_metrics),
            "avg_duration": avg_duration,
            "max_duration": max_duration,
            "min_duration": min_duration
        }


class MonitoringSystem:
    """监控系统主类"""
    
    def __init__(self, prometheus_port: int = 8000):
        self.prometheus_port = prometheus_port
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)
        
        self.is_running = False
        self.monitoring_tasks = []
        
        # 设置默认通知渠道
        self._setup_default_notifications()
    
    def _setup_default_notifications(self):
        """设置默认通知渠道"""
        def console_notification(alert: Alert):
            """控制台通知"""
            status_emoji = "🔥" if alert.status == AlertStatus.ACTIVE else "✅"
            print(f"{status_emoji} ALERT [{alert.severity.value.upper()}]: {alert.name}")
            print(f"   Description: {alert.description}")
            print(f"   Time: {alert.created_time}")
            if alert.resolved_time:
                print(f"   Resolved: {alert.resolved_time}")
        
        self.alert_manager.add_notification_channel("console", console_notification)
    
    async def start(self):
        """启动监控系统"""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info("Starting monitoring system...")
        
        # 启动Prometheus HTTP服务器
        if PROMETHEUS_AVAILABLE:
            try:
                start_http_server(self.prometheus_port, registry=self.metrics_collector.registry)
                self.logger.info(f"Prometheus metrics server started on port {self.prometheus_port}")
            except Exception as e:
                self.logger.error(f"Failed to start Prometheus server: {e}")
        
        # 启动监控任务
        self.monitoring_tasks = [
            asyncio.create_task(self._system_metrics_loop()),
            asyncio.create_task(self._alert_check_loop()),
            asyncio.create_task(self._health_check_loop())
        ]
        
        self.logger.info("Monitoring system started successfully")
    
    async def stop(self):
        """停止监控系统"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping monitoring system...")
        
        # 取消所有监控任务
        for task in self.monitoring_tasks:
            task.cancel()
        
        # 等待任务完成
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.logger.info("Monitoring system stopped")
    
    async def _system_metrics_loop(self):
        """系统指标收集循环"""
        while self.is_running:
            try:
                self.metrics_collector.update_system_metrics()
                await asyncio.sleep(10)  # 每10秒更新一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in system metrics loop: {e}")
                await asyncio.sleep(10)
    
    async def _alert_check_loop(self):
        """告警检查循环"""
        while self.is_running:
            try:
                await self.alert_manager.check_alerts()
                await asyncio.sleep(30)  # 每30秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.is_running:
            try:
                # 这里可以添加各种健康检查
                # 例如检查数据库连接、API响应等
                await asyncio.sleep(60)  # 每分钟检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)
    
    def add_business_alert(self, name: str, condition: Callable[[], bool],
                          severity: AlertSeverity, description: str = ""):
        """添加业务告警规则"""
        self.alert_manager.add_alert_rule(name, condition, severity, description)
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            "is_running": self.is_running,
            "uptime": time.time() - self.performance_monitor.start_time,
            "prometheus_port": self.prometheus_port,
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "alert_rules": len(self.alert_manager.alert_rules),
            "notification_channels": len(self.alert_manager.notification_channels)
        }


# 全局监控系统实例
monitoring_system = None

def get_monitoring_system() -> MonitoringSystem:
    """获取监控系统实例"""
    global monitoring_system
    if monitoring_system is None:
        monitoring_system = MonitoringSystem()
    return monitoring_system


# 使用示例
async def example_usage():
    """使用示例"""
    # 获取监控系统
    monitor = get_monitoring_system()
    
    # 添加自定义告警规则
    def check_high_latency():
        # 模拟检查延迟
        return False  # 假设延迟正常
    
    monitor.add_business_alert(
        "high_order_latency",
        check_high_latency,
        AlertSeverity.WARNING,
        "Order execution latency is too high"
    )
    
    # 启动监控系统
    await monitor.start()
    
    # 模拟业务指标记录
    metrics = monitor.metrics_collector
    
    # 记录订单
    metrics.record_order("filled", "BTC/USDT", "scalping_strategy")
    metrics.record_order_latency(0.05, "BTC/USDT", "market")
    
    # 更新损益和仓位
    metrics.update_pnl(1250.0, "scalping_strategy", "BTC/USDT")
    metrics.update_position(2.5, "BTC/USDT")
    
    # 记录交易量
    metrics.record_trade_volume(1.0, "BTC/USDT", "buy")
    
    # 记录API请求
    metrics.record_api_request("GET", "/api/orders", "200", 0.02)
    
    # 等待一段时间观察监控
    await asyncio.sleep(30)
    
    # 查看监控状态
    status = monitor.get_monitoring_status()
    print(f"Monitoring status: {status}")
    
    # 查看告警统计
    alert_stats = monitor.alert_manager.get_alert_statistics()
    print(f"Alert statistics: {alert_stats}")
    
    # 查看性能摘要
    perf_summary = monitor.performance_monitor.get_performance_summary()
    print(f"Performance summary: {perf_summary}")
    
    # 停止监控系统
    await monitor.stop()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
