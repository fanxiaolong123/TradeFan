"""
TradeFan 策略实现层
包含各种类型的交易策略实现
按策略类型分类组织
"""

# 基类
from .base_strategy import BaseStrategy

# 趋势策略
from .trend import (
    TrendFollowingStrategy,
    AdvancedTrendFollowingStrategy,
    BreakoutStrategy,
    MomentumStrategy,
    DonchianRSIADXStrategy,
    TrendMABreakoutStrategy
)

# 均值回归策略
from .mean_reversion import (
    MeanReversionStrategy,
    ReversalBollingerStrategy
)

# 剥头皮策略
from .scalping import (
    ScalpingStrategy,
    AdvancedScalpingStrategy
)

# 策略配置模板
from .strategy_templates import STRATEGY_TEMPLATES

__all__ = [
    # 基类
    'BaseStrategy',
    
    # 趋势策略
    'TrendFollowingStrategy',
    'AdvancedTrendFollowingStrategy',
    'BreakoutStrategy',
    'MomentumStrategy',
    'DonchianRSIADXStrategy',
    'TrendMABreakoutStrategy',
    
    # 均值回归策略
    'MeanReversionStrategy',
    'ReversalBollingerStrategy',
    
    # 剥头皮策略
    'ScalpingStrategy',
    'AdvancedScalpingStrategy',
    
    # 配置模板
    'STRATEGY_TEMPLATES'
]

__version__ = '2.0.0'
__author__ = 'TradeFan Team'
