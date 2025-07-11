"""
策略模块包
提供策略基类和策略注册机制
"""

from .base_strategy import BaseStrategy
from .trend_ma_breakout import TrendMABreakoutStrategy
from .donchian_rsi_adx import DonchianRSIADXStrategy
from .reversal_bollinger import ReversalBollingerStrategy

# 策略注册表
STRATEGY_REGISTRY = {
    'trend_ma_breakout': TrendMABreakoutStrategy,
    'donchian_rsi_adx': DonchianRSIADXStrategy,
    'reversal_bollinger': ReversalBollingerStrategy,
}

def get_strategy(strategy_name: str, **kwargs):
    """获取策略实例"""
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {strategy_name}. 可用策略: {list(STRATEGY_REGISTRY.keys())}")
    
    strategy_class = STRATEGY_REGISTRY[strategy_name]
    return strategy_class(**kwargs)

def list_strategies():
    """列出所有可用策略"""
    return list(STRATEGY_REGISTRY.keys())

__all__ = ['BaseStrategy', 'get_strategy', 'list_strategies', 'STRATEGY_REGISTRY']
