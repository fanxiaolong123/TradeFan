"""
TradeFan 策略框架层
提供策略开发、管理、组合的统一框架
与core层分离，专注于策略相关功能
"""

# 策略基础组件
from .strategy_base import BaseStrategy, StrategyState, StrategyMetrics
from .signal import Signal, SignalType
from .strategy_manager import StrategyManager, StrategyFactory
from .portfolio import StrategyPortfolio
from .metrics import PerformanceMetrics

__all__ = [
    # 策略基础
    'BaseStrategy',
    'StrategyState', 
    'StrategyMetrics',
    
    # 信号系统
    'Signal',
    'SignalType',
    
    # 策略管理
    'StrategyManager',
    'StrategyFactory',
    
    # 组合管理
    'StrategyPortfolio',
    
    # 性能指标
    'PerformanceMetrics'
]

__version__ = '2.0.0'
__author__ = 'TradeFan Team'
