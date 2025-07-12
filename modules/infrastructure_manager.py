"""
TradeFan 基础设施管理器
统一管理数据基础设施、订单管理、监控系统等核心组件
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import signal
import sys

from .data_infrastructure import DataInfrastructureManager, DataInfrastructureConfig
from .order_management_system import OrderManager, OrderRequest, OrderStatus
from .monitoring_system import MonitoringSystem, AlertSeverity
from .config_manager import ConfigManager, TradeFanConfig


class InfrastructureManager:
    """基础设施管理器"""
    
    def __init__(self, config_path: str = "config"):
        self.logger = logging.getLogger(__name__)
        
        # 配置管理
        self.config_manager = ConfigManager(config_path)
        self.config: Optional[TradeFanConfig] = None
        
        # 核心组件
        self.data_infrastructure: Optional[DataInfrastructureManager] = None
        self.order_manager: Optional[OrderManager] = None
        self.monitoring_system: Optional[MonitoringSystem] = None
        
        # 状态管理
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        self.shutdown_handlers: List[callable] = []
        
        # 注册信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self, environment: str = "development") -> bool:
        """初始化基础设施"""
        try:
            self.logger.info(f"Initializing TradeFan infrastructure for {environment}...")
            
            # 1. 加载配置
            self.config = self.config_manager.load_config(environment)
            if not self.config:
                self.logger.error("Failed to load configuration")
                return False
            
            # 2. 初始化数据基础设施
            await self._initialize_data_infrastructure()
            
            # 3. 初始化订单管理系统
            await self._initialize_order_management()
            
            # 4. 初始化监控系统
            await self._initialize_monitoring_system()
            
            # 5. 设置组件间集成
            await self._setup_integrations()
            
            # 6. 执行健康检查
            health_status = await self.health_check()
            if not all(health_status.values()):
                self.logger.warning(f"Some components are unhealthy: {health_status}")
            
            self.is_running = True
            self.startup_time = datetime.now(timezone.utc)
            
            self.logger.info("TradeFan infrastructure initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize infrastructure: {e}")
            return False
    
    async def _initialize_data_infrastructure(self):
        """初始化数据基础设施"""
        self.logger.info("Initializing data infrastructure...")
        
        # 创建数据基础设施配置
        data_config = DataInfrastructureConfig()
        data_config.influx_url = self.config.database.influx_url
        data_config.influx_token = self.config.database.influx_token
        data_config.influx_org = self.config.database.influx_org
        data_config.influx_bucket = self.config.database.influx_bucket
        data_config.redis_host = self.config.database.redis_host
        data_config.redis_port = self.config.database.redis_port
        data_config.redis_password = self.config.database.redis_password
        
        self.data_infrastructure = DataInfrastructureManager(data_config)
        
        # 测试连接
        health = await self.data_infrastructure.health_check()
        self.logger.info(f"Data infrastructure health: {health}")
    
    async def _initialize_order_management(self):
        """初始化订单管理系统"""
        self.logger.info("Initializing order management system...")
        
        self.order_manager = OrderManager()
        
        # 设置风控参数
        risk_engine = self.order_manager.risk_engine
        
        # 从配置设置风控参数
        for exchange_config in self.config.exchanges:
            for symbol in exchange_config.symbols:
                # 设置仓位限制 (基于初始资金的一定比例)
                max_position = self.config.trading.initial_capital * 0.1  # 10%
                risk_engine.set_position_limit(symbol, max_position)
        
        # 设置日损失限制
        max_daily_loss = self.config.trading.initial_capital * self.config.trading.max_daily_loss
        risk_engine.set_daily_loss_limit("default", max_daily_loss)
        
        self.logger.info("Order management system initialized")
    
    async def _initialize_monitoring_system(self):
        """初始化监控系统"""
        self.logger.info("Initializing monitoring system...")
        
        prometheus_port = self.config.monitoring.prometheus_port
        self.monitoring_system = MonitoringSystem(prometheus_port)
        
        # 添加业务告警规则
        self._setup_business_alerts()
        
        # 启动监控系统
        await self.monitoring_system.start()
        
        self.logger.info("Monitoring system initialized")
    
    def _setup_business_alerts(self):
        """设置业务告警规则"""
        monitor = self.monitoring_system
        
        # 高延迟告警
        def check_high_latency():
            # 这里应该检查实际的延迟指标
            return False  # 简化实现
        
        monitor.add_business_alert(
            "high_order_latency",
            check_high_latency,
            AlertSeverity.WARNING,
            "Order execution latency is too high"
        )
        
        # 高损失告警
        def check_high_loss():
            if self.order_manager:
                # 检查当日损失
                daily_pnl = self.order_manager.risk_engine.daily_pnl.get("default", 0.0)
                max_loss = self.config.trading.initial_capital * self.config.trading.max_daily_loss
                return daily_pnl < -max_loss
            return False
        
        monitor.add_business_alert(
            "high_daily_loss",
            check_high_loss,
            AlertSeverity.CRITICAL,
            "Daily loss limit exceeded"
        )
        
        # 连接断开告警
        def check_connection_health():
            if self.data_infrastructure:
                # 这里应该检查实际的连接状态
                return False  # 简化实现
            return True
        
        monitor.add_business_alert(
            "connection_failure",
            check_connection_health,
            AlertSeverity.CRITICAL,
            "Database or cache connection failed"
        )
    
    async def _setup_integrations(self):
        """设置组件间集成"""
        self.logger.info("Setting up component integrations...")
        
        # 订单管理系统集成监控
        if self.order_manager and self.monitoring_system:
            metrics = self.monitoring_system.metrics_collector
            
            # 订单更新回调
            async def on_order_update(order):
                metrics.record_order(
                    order.status.value,
                    order.symbol,
                    order.strategy_id or "default"
                )
                
                # 记录到数据基础设施
                if self.data_infrastructure:
                    order_data = {
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "side": order.side.value,
                        "status": order.status.value,
                        "quantity": order.quantity,
                        "filled_quantity": order.filled_quantity,
                        "avg_fill_price": order.avg_fill_price,
                        "timestamp": order.updated_time
                    }
                    # 这里可以存储订单数据到InfluxDB
            
            # 成交回调
            async def on_fill(order, quantity, price):
                metrics.record_trade_volume(quantity, order.symbol, order.side.value)
                
                # 更新PnL指标
                pnl_change = 0.0  # 这里应该计算实际的PnL变化
                metrics.update_pnl(pnl_change, order.strategy_id or "default", order.symbol)
                
                # 更新仓位指标
                position_change = quantity if order.side.value == "buy" else -quantity
                current_position = 0.0  # 这里应该获取当前仓位
                metrics.update_position(current_position + position_change, order.symbol)
            
            self.order_manager.add_order_update_callback(on_order_update)
            self.order_manager.add_fill_callback(on_fill)
        
        # 配置变更监听
        def on_config_change(new_config):
            self.logger.info("Configuration changed, updating components...")
            # 这里可以实现热更新逻辑
        
        self.config_manager.add_config_watcher(on_config_change)
    
    async def submit_order(self, order_request: OrderRequest):
        """提交订单"""
        if not self.order_manager:
            raise RuntimeError("Order management system not initialized")
        
        # 记录订单提交指标
        if self.monitoring_system:
            start_time = asyncio.get_event_loop().time()
            
        order = await self.order_manager.submit_order(order_request)
        
        if self.monitoring_system:
            end_time = asyncio.get_event_loop().time()
            latency = end_time - start_time
            self.monitoring_system.metrics_collector.record_order_latency(
                latency, order_request.symbol, order_request.order_type.value
            )
        
        return order
    
    async def store_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """存储市场数据"""
        if not self.data_infrastructure:
            raise RuntimeError("Data infrastructure not initialized")
        
        await self.data_infrastructure.store_market_data(symbol, timeframe, data)
        
        # 记录数据处理指标
        if self.monitoring_system:
            self.monitoring_system.metrics_collector.record_data_point(
                "market_data", timeframe
            )
    
    async def store_indicators(self, symbol: str, timeframe: str, indicators: Dict[str, float]):
        """存储技术指标"""
        if not self.data_infrastructure:
            raise RuntimeError("Data infrastructure not initialized")
        
        await self.data_infrastructure.store_indicators(symbol, timeframe, indicators)
        
        # 记录指标处理
        if self.monitoring_system:
            self.monitoring_system.metrics_collector.record_data_point(
                "indicators", timeframe, len(indicators)
            )
    
    async def get_market_data(self, symbol: str, timeframe: str, **kwargs):
        """获取市场数据"""
        if not self.data_infrastructure:
            raise RuntimeError("Data infrastructure not initialized")
        
        return await self.data_infrastructure.get_market_data(symbol, timeframe, **kwargs)
    
    async def get_indicators(self, symbol: str, timeframe: str, **kwargs):
        """获取技术指标"""
        if not self.data_infrastructure:
            raise RuntimeError("Data infrastructure not initialized")
        
        return await self.data_infrastructure.get_indicators(symbol, timeframe, **kwargs)
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        health_status = {
            "infrastructure_manager": self.is_running,
            "data_infrastructure": False,
            "order_manager": False,
            "monitoring_system": False
        }
        
        try:
            # 检查数据基础设施
            if self.data_infrastructure:
                data_health = await self.data_infrastructure.health_check()
                health_status["data_infrastructure"] = all(data_health.values())
            
            # 检查订单管理系统
            if self.order_manager:
                health_status["order_manager"] = True  # 简化检查
            
            # 检查监控系统
            if self.monitoring_system:
                monitor_status = self.monitoring_system.get_monitoring_status()
                health_status["monitoring_system"] = monitor_status["is_running"]
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
        
        return health_status
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "is_running": self.is_running,
            "startup_time": self.startup_time,
            "uptime_seconds": 0,
            "environment": self.config.environment if self.config else "unknown",
            "version": self.config.version if self.config else "unknown"
        }
        
        if self.startup_time:
            uptime = datetime.now(timezone.utc) - self.startup_time
            status["uptime_seconds"] = uptime.total_seconds()
        
        # 添加组件状态
        if self.order_manager:
            order_stats = self.order_manager.get_order_statistics()
            status["order_statistics"] = order_stats
        
        if self.monitoring_system:
            monitor_status = self.monitoring_system.get_monitoring_status()
            status["monitoring_status"] = monitor_status
        
        return status
    
    def add_shutdown_handler(self, handler: callable):
        """添加关闭处理器"""
        self.shutdown_handlers.append(handler)
    
    async def shutdown(self):
        """关闭基础设施"""
        if not self.is_running:
            return
        
        self.logger.info("Shutting down TradeFan infrastructure...")
        self.is_running = False
        
        try:
            # 执行自定义关闭处理器
            for handler in self.shutdown_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler()
                    else:
                        handler()
                except Exception as e:
                    self.logger.error(f"Error in shutdown handler: {e}")
            
            # 关闭监控系统
            if self.monitoring_system:
                await self.monitoring_system.stop()
            
            # 关闭数据基础设施
            if self.data_infrastructure:
                await self.data_infrastructure.close()
            
            self.logger.info("TradeFan infrastructure shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# 全局基础设施管理器实例
infrastructure_manager = None

def get_infrastructure_manager() -> InfrastructureManager:
    """获取基础设施管理器实例"""
    global infrastructure_manager
    if infrastructure_manager is None:
        infrastructure_manager = InfrastructureManager()
    return infrastructure_manager


# 使用示例
async def example_usage():
    """使用示例"""
    # 获取基础设施管理器
    infra = get_infrastructure_manager()
    
    # 初始化基础设施
    success = await infra.initialize("development")
    if not success:
        print("Failed to initialize infrastructure")
        return
    
    # 模拟存储市场数据
    market_data = {
        "open": 45000.0,
        "high": 45100.0,
        "low": 44900.0,
        "close": 45050.0,
        "volume": 1234.56,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await infra.store_market_data("BTC/USDT", "1m", market_data)
    
    # 模拟存储技术指标
    indicators = {
        "ema_fast": 45025.0,
        "ema_slow": 44980.0,
        "rsi": 65.5,
        "macd": 12.3
    }
    
    await infra.store_indicators("BTC/USDT", "1m", indicators)
    
    # 模拟提交订单
    from .order_management_system import OrderRequest, OrderSide, OrderType
    
    order_request = OrderRequest(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        strategy_id="scalping_strategy"
    )
    
    order = await infra.submit_order(order_request)
    if order:
        print(f"Order submitted: {order.order_id}")
    
    # 健康检查
    health = await infra.health_check()
    print(f"Health status: {health}")
    
    # 系统状态
    status = infra.get_system_status()
    print(f"System status: {status}")
    
    # 等待一段时间
    await asyncio.sleep(10)
    
    # 关闭基础设施
    await infra.shutdown()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
