"""
TradeFan 核心基础设施模块 v2.0
提供统一的API客户端、配置管理、日志管理等基础服务
策略相关功能已移动到framework/层
"""

# 基础设施组件
from .api_client import APIClient
from .config_manager import ConfigManager
from .logger import LoggerManager
from .trading_executor import TradingExecutor

# 技术指标
from .indicators import TechnicalIndicators

__all__ = [
    # 基础设施
    'APIClient',
    'ConfigManager', 
    'LoggerManager',
    'TradingExecutor',
    
    # 技术指标
    'TechnicalIndicators'
]

__version__ = '2.0.0'
__author__ = 'TradeFan Team'
