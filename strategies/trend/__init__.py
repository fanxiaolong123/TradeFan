"""
趋势策略模块
包含各种趋势跟踪和趋势突破策略
"""

from .trend_following import TrendFollowingStrategy
from .trend_following_strategy import TrendFollowingStrategy as AdvancedTrendFollowingStrategy
from .breakout import BreakoutStrategy
from .momentum import MomentumStrategy
from .donchian_rsi_adx import DonchianRSIADXStrategy
from .trend_ma_breakout import TrendMABreakoutStrategy

__all__ = [
    'TrendFollowingStrategy',
    'AdvancedTrendFollowingStrategy',
    'BreakoutStrategy',
    'MomentumStrategy',
    'DonchianRSIADXStrategy',
    'TrendMABreakoutStrategy'
]
