"""
TradeFan 配置管理系统
支持多环境配置、热更新和配置验证
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
from datetime import datetime


@dataclass
class DatabaseConfig:
    """数据库配置"""
    # InfluxDB配置
    influx_url: str = "http://localhost:8086"
    influx_token: str = "your-token-here"
    influx_org: str = "tradefan"
    influx_bucket: str = "market_data"
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None


@dataclass
class TradingConfig:
    """交易配置"""
    # 基础配置
    initial_capital: float = 10000.0
    max_positions: int = 3
    max_risk_per_trade: float = 0.01
    
    # 风控配置
    stop_loss: float = 0.02
    take_profit: float = 0.04
    max_daily_loss: float = 0.05
    max_drawdown: float = 0.10
    
    # 执行配置
    order_timeout: int = 300  # 秒
    max_slippage: float = 0.001
    min_order_size: float = 0.001


@dataclass
class StrategyConfig:
    """策略配置"""
    # 短线策略参数
    ema_fast: int = 8
    ema_medium: int = 21
    ema_slow: int = 55
    bb_period: int = 20
    bb_std: float = 2.0
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # 信号阈值
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    signal_threshold: float = 0.6
    
    # 时间框架
    timeframes: List[str] = field(default_factory=lambda: ["5m", "15m", "30m", "1h"])


@dataclass
class MonitoringConfig:
    """监控配置"""
    prometheus_port: int = 8000
    log_level: str = "INFO"
    log_file: str = "logs/tradefan.log"
    
    # 告警配置
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    
    # 性能配置
    metrics_retention_days: int = 30
    health_check_interval: int = 60


@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = True
    rate_limit: int = 1200  # 每分钟请求数
    
    # 支持的交易对
    symbols: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])


@dataclass
class TradeFanConfig:
    """TradeFan主配置"""
    environment: str = "development"
    debug: bool = True
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    exchanges: List[ExchangeConfig] = field(default_factory=list)
    
    # 元数据
    version: str = "2.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_trading_config(config: TradingConfig) -> List[str]:
        """验证交易配置"""
        errors = []
        
        if config.initial_capital <= 0:
            errors.append("Initial capital must be positive")
        
        if config.max_risk_per_trade <= 0 or config.max_risk_per_trade > 1:
            errors.append("Max risk per trade must be between 0 and 1")
        
        if config.stop_loss <= 0 or config.stop_loss > 1:
            errors.append("Stop loss must be between 0 and 1")
        
        if config.take_profit <= 0:
            errors.append("Take profit must be positive")
        
        if config.max_positions <= 0:
            errors.append("Max positions must be positive")
        
        return errors
    
    @staticmethod
    def validate_strategy_config(config: StrategyConfig) -> List[str]:
        """验证策略配置"""
        errors = []
        
        if config.ema_fast >= config.ema_medium:
            errors.append("EMA fast period must be less than medium period")
        
        if config.ema_medium >= config.ema_slow:
            errors.append("EMA medium period must be less than slow period")
        
        if config.bb_period <= 0:
            errors.append("Bollinger Bands period must be positive")
        
        if config.bb_std <= 0:
            errors.append("Bollinger Bands standard deviation must be positive")
        
        if config.rsi_period <= 0:
            errors.append("RSI period must be positive")
        
        if not (0 < config.rsi_oversold < config.rsi_overbought < 100):
            errors.append("RSI thresholds must be: 0 < oversold < overbought < 100")
        
        return errors
    
    @staticmethod
    def validate_database_config(config: DatabaseConfig) -> List[str]:
        """验证数据库配置"""
        errors = []
        
        if not config.influx_url:
            errors.append("InfluxDB URL is required")
        
        if not config.influx_token:
            errors.append("InfluxDB token is required")
        
        if not config.influx_org:
            errors.append("InfluxDB organization is required")
        
        if not config.influx_bucket:
            errors.append("InfluxDB bucket is required")
        
        if not config.redis_host:
            errors.append("Redis host is required")
        
        if config.redis_port <= 0 or config.redis_port > 65535:
            errors.append("Redis port must be between 1 and 65535")
        
        return errors
    
    @classmethod
    def validate_config(cls, config: TradeFanConfig) -> List[str]:
        """验证完整配置"""
        all_errors = []
        
        # 验证各个子配置
        all_errors.extend(cls.validate_trading_config(config.trading))
        all_errors.extend(cls.validate_strategy_config(config.strategy))
        all_errors.extend(cls.validate_database_config(config.database))
        
        # 验证环境
        valid_environments = ["development", "testing", "staging", "production"]
        if config.environment not in valid_environments:
            all_errors.append(f"Environment must be one of: {valid_environments}")
        
        return all_errors


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.current_config: Optional[TradeFanConfig] = None
        self.config_watchers: List[callable] = []
        self.logger = logging.getLogger(__name__)
        
        # 创建环境配置目录
        self.environments_dir = self.config_dir / "environments"
        self.environments_dir.mkdir(exist_ok=True)
    
    def add_config_watcher(self, callback: callable):
        """添加配置变更监听器"""
        self.config_watchers.append(callback)
    
    def load_config(self, environment: str = "development") -> TradeFanConfig:
        """加载配置"""
        try:
            config_file = self.environments_dir / f"{environment}.yaml"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 转换为配置对象
                config = self._dict_to_config(config_data)
                config.environment = environment
                
            else:
                # 创建默认配置
                config = TradeFanConfig(environment=environment)
                self.save_config(config)
            
            # 验证配置
            errors = ConfigValidator.validate_config(config)
            if errors:
                self.logger.warning(f"Configuration validation errors: {errors}")
            
            self.current_config = config
            self.logger.info(f"Loaded configuration for environment: {environment}")
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            # 返回默认配置
            return TradeFanConfig(environment=environment)
    
    def save_config(self, config: TradeFanConfig):
        """保存配置"""
        try:
            config.updated_at = datetime.now()
            config_file = self.environments_dir / f"{config.environment}.yaml"
            
            # 转换为字典
            config_dict = self._config_to_dict(config)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Saved configuration for environment: {config.environment}")
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """更新配置"""
        if not self.current_config:
            return False
        
        try:
            # 应用更新
            self._apply_updates(self.current_config, updates)
            
            # 验证更新后的配置
            errors = ConfigValidator.validate_config(self.current_config)
            if errors:
                self.logger.error(f"Configuration validation failed after update: {errors}")
                return False
            
            # 保存配置
            self.save_config(self.current_config)
            
            # 通知监听器
            self._notify_watchers()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    def get_config(self) -> Optional[TradeFanConfig]:
        """获取当前配置"""
        return self.current_config
    
    def reload_config(self):
        """重新加载配置"""
        if self.current_config:
            environment = self.current_config.environment
            self.load_config(environment)
            self._notify_watchers()
    
    def _dict_to_config(self, data: Dict[str, Any]) -> TradeFanConfig:
        """字典转配置对象"""
        config = TradeFanConfig()
        
        # 基础配置
        config.environment = data.get("environment", "development")
        config.debug = data.get("debug", True)
        config.version = data.get("version", "2.0.0")
        
        # 数据库配置
        if "database" in data:
            db_data = data["database"]
            config.database = DatabaseConfig(
                influx_url=db_data.get("influx_url", "http://localhost:8086"),
                influx_token=db_data.get("influx_token", "your-token-here"),
                influx_org=db_data.get("influx_org", "tradefan"),
                influx_bucket=db_data.get("influx_bucket", "market_data"),
                redis_host=db_data.get("redis_host", "localhost"),
                redis_port=db_data.get("redis_port", 6379),
                redis_db=db_data.get("redis_db", 0),
                redis_password=db_data.get("redis_password")
            )
        
        # 交易配置
        if "trading" in data:
            trading_data = data["trading"]
            config.trading = TradingConfig(
                initial_capital=trading_data.get("initial_capital", 10000.0),
                max_positions=trading_data.get("max_positions", 3),
                max_risk_per_trade=trading_data.get("max_risk_per_trade", 0.01),
                stop_loss=trading_data.get("stop_loss", 0.02),
                take_profit=trading_data.get("take_profit", 0.04),
                max_daily_loss=trading_data.get("max_daily_loss", 0.05),
                max_drawdown=trading_data.get("max_drawdown", 0.10),
                order_timeout=trading_data.get("order_timeout", 300),
                max_slippage=trading_data.get("max_slippage", 0.001),
                min_order_size=trading_data.get("min_order_size", 0.001)
            )
        
        # 策略配置
        if "strategy" in data:
            strategy_data = data["strategy"]
            config.strategy = StrategyConfig(
                ema_fast=strategy_data.get("ema_fast", 8),
                ema_medium=strategy_data.get("ema_medium", 21),
                ema_slow=strategy_data.get("ema_slow", 55),
                bb_period=strategy_data.get("bb_period", 20),
                bb_std=strategy_data.get("bb_std", 2.0),
                rsi_period=strategy_data.get("rsi_period", 14),
                macd_fast=strategy_data.get("macd_fast", 12),
                macd_slow=strategy_data.get("macd_slow", 26),
                macd_signal=strategy_data.get("macd_signal", 9),
                rsi_oversold=strategy_data.get("rsi_oversold", 30.0),
                rsi_overbought=strategy_data.get("rsi_overbought", 70.0),
                signal_threshold=strategy_data.get("signal_threshold", 0.6),
                timeframes=strategy_data.get("timeframes", ["5m", "15m", "30m", "1h"])
            )
        
        # 监控配置
        if "monitoring" in data:
            monitoring_data = data["monitoring"]
            config.monitoring = MonitoringConfig(
                prometheus_port=monitoring_data.get("prometheus_port", 8000),
                log_level=monitoring_data.get("log_level", "INFO"),
                log_file=monitoring_data.get("log_file", "logs/tradefan.log"),
                alert_email=monitoring_data.get("alert_email"),
                alert_webhook=monitoring_data.get("alert_webhook"),
                metrics_retention_days=monitoring_data.get("metrics_retention_days", 30),
                health_check_interval=monitoring_data.get("health_check_interval", 60)
            )
        
        # 交易所配置
        if "exchanges" in data:
            config.exchanges = []
            for exchange_data in data["exchanges"]:
                exchange = ExchangeConfig(
                    name=exchange_data.get("name", "binance"),
                    api_key=exchange_data.get("api_key", ""),
                    api_secret=exchange_data.get("api_secret", ""),
                    sandbox=exchange_data.get("sandbox", True),
                    rate_limit=exchange_data.get("rate_limit", 1200),
                    symbols=exchange_data.get("symbols", ["BTC/USDT", "ETH/USDT"])
                )
                config.exchanges.append(exchange)
        
        return config
    
    def _config_to_dict(self, config: TradeFanConfig) -> Dict[str, Any]:
        """配置对象转字典"""
        return {
            "environment": config.environment,
            "debug": config.debug,
            "version": config.version,
            "database": {
                "influx_url": config.database.influx_url,
                "influx_token": config.database.influx_token,
                "influx_org": config.database.influx_org,
                "influx_bucket": config.database.influx_bucket,
                "redis_host": config.database.redis_host,
                "redis_port": config.database.redis_port,
                "redis_db": config.database.redis_db,
                "redis_password": config.database.redis_password
            },
            "trading": {
                "initial_capital": config.trading.initial_capital,
                "max_positions": config.trading.max_positions,
                "max_risk_per_trade": config.trading.max_risk_per_trade,
                "stop_loss": config.trading.stop_loss,
                "take_profit": config.trading.take_profit,
                "max_daily_loss": config.trading.max_daily_loss,
                "max_drawdown": config.trading.max_drawdown,
                "order_timeout": config.trading.order_timeout,
                "max_slippage": config.trading.max_slippage,
                "min_order_size": config.trading.min_order_size
            },
            "strategy": {
                "ema_fast": config.strategy.ema_fast,
                "ema_medium": config.strategy.ema_medium,
                "ema_slow": config.strategy.ema_slow,
                "bb_period": config.strategy.bb_period,
                "bb_std": config.strategy.bb_std,
                "rsi_period": config.strategy.rsi_period,
                "macd_fast": config.strategy.macd_fast,
                "macd_slow": config.strategy.macd_slow,
                "macd_signal": config.strategy.macd_signal,
                "rsi_oversold": config.strategy.rsi_oversold,
                "rsi_overbought": config.strategy.rsi_overbought,
                "signal_threshold": config.strategy.signal_threshold,
                "timeframes": config.strategy.timeframes
            },
            "monitoring": {
                "prometheus_port": config.monitoring.prometheus_port,
                "log_level": config.monitoring.log_level,
                "log_file": config.monitoring.log_file,
                "alert_email": config.monitoring.alert_email,
                "alert_webhook": config.monitoring.alert_webhook,
                "metrics_retention_days": config.monitoring.metrics_retention_days,
                "health_check_interval": config.monitoring.health_check_interval
            },
            "exchanges": [
                {
                    "name": exchange.name,
                    "api_key": exchange.api_key,
                    "api_secret": exchange.api_secret,
                    "sandbox": exchange.sandbox,
                    "rate_limit": exchange.rate_limit,
                    "symbols": exchange.symbols
                }
                for exchange in config.exchanges
            ]
        }
    
    def _apply_updates(self, config: TradeFanConfig, updates: Dict[str, Any]):
        """应用配置更新"""
        for key, value in updates.items():
            if hasattr(config, key):
                if isinstance(value, dict) and hasattr(getattr(config, key), '__dict__'):
                    # 递归更新嵌套对象
                    nested_obj = getattr(config, key)
                    for nested_key, nested_value in value.items():
                        if hasattr(nested_obj, nested_key):
                            setattr(nested_obj, nested_key, nested_value)
                else:
                    setattr(config, key, value)
    
    def _notify_watchers(self):
        """通知配置监听器"""
        for watcher in self.config_watchers:
            try:
                if asyncio.iscoroutinefunction(watcher):
                    asyncio.create_task(watcher(self.current_config))
                else:
                    watcher(self.current_config)
            except Exception as e:
                self.logger.error(f"Error notifying config watcher: {e}")
    
    def create_environment_configs(self):
        """创建所有环境的默认配置"""
        environments = {
            "development": {
                "debug": True,
                "database": {
                    "influx_url": "http://localhost:8086",
                    "redis_host": "localhost"
                },
                "trading": {
                    "initial_capital": 10000.0
                }
            },
            "testing": {
                "debug": True,
                "database": {
                    "influx_url": "http://localhost:8086",
                    "redis_host": "localhost"
                },
                "trading": {
                    "initial_capital": 1000.0
                }
            },
            "staging": {
                "debug": False,
                "database": {
                    "influx_url": "http://staging-influx:8086",
                    "redis_host": "staging-redis"
                },
                "trading": {
                    "initial_capital": 50000.0
                }
            },
            "production": {
                "debug": False,
                "database": {
                    "influx_url": "http://prod-influx:8086",
                    "redis_host": "prod-redis"
                },
                "trading": {
                    "initial_capital": 100000.0
                }
            }
        }
        
        for env_name, env_config in environments.items():
            config = TradeFanConfig(environment=env_name)
            self._apply_updates(config, env_config)
            self.save_config(config)
        
        self.logger.info("Created default configurations for all environments")


# 全局配置管理器实例
config_manager = None

def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager


def get_config(environment: str = None) -> TradeFanConfig:
    """获取配置"""
    manager = get_config_manager()
    if environment:
        return manager.load_config(environment)
    elif manager.current_config:
        return manager.current_config
    else:
        return manager.load_config("development")


# 使用示例
async def example_usage():
    """使用示例"""
    # 获取配置管理器
    manager = get_config_manager()
    
    # 创建所有环境的默认配置
    manager.create_environment_configs()
    
    # 加载开发环境配置
    config = manager.load_config("development")
    print(f"Loaded config for {config.environment}")
    print(f"Initial capital: {config.trading.initial_capital}")
    
    # 更新配置
    updates = {
        "trading": {
            "initial_capital": 15000.0,
            "max_positions": 5
        },
        "strategy": {
            "ema_fast": 10
        }
    }
    
    success = manager.update_config(updates)
    print(f"Config update success: {success}")
    
    # 验证配置
    errors = ConfigValidator.validate_config(config)
    if errors:
        print(f"Validation errors: {errors}")
    else:
        print("Configuration is valid")
    
    # 添加配置监听器
    def on_config_change(new_config):
        print(f"Configuration changed for environment: {new_config.environment}")
    
    manager.add_config_watcher(on_config_change)
    
    # 重新加载配置
    manager.reload_config()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
