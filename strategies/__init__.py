"""
TradeFan 策略实现层
包含各种类型的交易策略实现
按策略类型分类组织
"""

# 趋势策略 (已实现)
from .trend.trend_following import TrendFollowingStrategy

# 策略配置模板
from .strategy_templates import STRATEGY_TEMPLATES

__all__ = [
    # 趋势策略
    'TrendFollowingStrategy',
    
    # 配置模板
    'STRATEGY_TEMPLATES'
]

__version__ = '2.0.0'
__author__ = 'TradeFan Team'
