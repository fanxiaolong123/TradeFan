"""
TradeFan 策略工程工具包 - 技术指标武器库
========================================

一个全面的技术分析指标库，支持趋势、动量、波动性、成交量等各类指标计算。
不依赖TA-Lib，使用纯Python实现，便于维护和扩展。

使用示例:
    from indicators_lib import trend, momentum, volatility
    
    # 计算EMA
    df['ema_12'] = trend.ema(df['close'], 12)
    
    # 计算RSI
    df['rsi_14'] = momentum.rsi(df['close'], 14)
    
    # 计算布林带
    upper, mid, lower = volatility.bollinger_bands(df['close'], 20)

Author: TradeFan Team
Version: 1.0.0
"""

from . import trend
from . import momentum  
from . import volatility
from . import volume
from . import risk
from . import composite

# 统一导入所有指标函数
from .trend import *
from .momentum import *
from .volatility import *
from .volume import *
from .risk import *
from .composite import *

# 指标函数映射字典，支持动态调用
def _build_indicator_map():
    """构建指标映射字典，避免导入时的循环引用问题"""
    return {
        # 趋势指标
        'ema': trend.ema,
        'sma': trend.sma,
        'macd': trend.macd,
        'adx': trend.adx,
        'parabolic_sar': trend.parabolic_sar,
        'dema': trend.dema,
        'tema': trend.tema,
        'wma': trend.wma,
        'hma': trend.hma,
        'vwap': trend.vwap,
        'ppo': trend.ppo,
        'trix': trend.trix,
        'aroon': trend.aroon,
        
        # 动量指标
        'rsi': momentum.rsi,
        'cci': momentum.cci,
        'roc': momentum.roc,
        'momentum': momentum.momentum,
        'stochastic_kd': momentum.stochastic_kd,
        'williams_r': momentum.williams_r,
        'ultimate_oscillator': momentum.ultimate_oscillator,
        'awesome_oscillator': momentum.awesome_oscillator,
        'mfi': momentum.mfi,
        'stoch_rsi': momentum.stoch_rsi,
        'tsi': momentum.tsi,
        'dpo': momentum.dpo,
        'ppo': momentum.ppo,
        'kama': momentum.kama,
        
        # 波动性指标
        'atr': volatility.atr,
        'bollinger_bands': volatility.bollinger_bands,
        'donchian_channel': volatility.donchian_channel,
        'keltner_channel': volatility.keltner_channel,
        'volatility': volatility.volatility,
        'natr': volatility.natr,
        'std_dev': volatility.std_dev,
        'ulcer_index': volatility.ulcer_index,
        'mass_index': volatility.mass_index,
        'chaikin_volatility': volatility.chaikin_volatility,
        
        # 成交量指标
        'obv': volume.obv,
        'volume_sma': volume.volume_sma,
        'chaikin_money_flow': volume.chaikin_money_flow,
        'accumulation_distribution': volume.accumulation_distribution,
        'volume_rate_of_change': volume.volume_rate_of_change,
        'ease_of_movement': volume.ease_of_movement,
        'volume_oscillator': volume.volume_oscillator,
        'price_volume_trend': volume.price_volume_trend,
        'klinger_oscillator': volume.klinger_oscillator,
        'force_index': volume.force_index,
        
        # 风险指标
        'sharpe_ratio': risk.sharpe_ratio,
        'max_drawdown': risk.max_drawdown,
        'sortino_ratio': risk.sortino_ratio,
        'calmar_ratio': risk.calmar_ratio,
        'var': risk.var,
        'cvar': risk.cvar,
        'beta': risk.beta,
        'alpha': risk.alpha,
        'information_ratio': risk.information_ratio,
        'tracking_error': risk.tracking_error,
        
        # 组合指标
        'trend_strength_indicator': composite.trend_strength_indicator,
        'volatility_breakout': composite.volatility_breakout,
        'support_resistance': composite.support_resistance,
        'ichimoku_cloud': composite.ichimoku_cloud,
        'pivot_points': composite.pivot_points,
        'momentum_divergence': composite.momentum_divergence,
        'multi_timeframe_signal': composite.multi_timeframe_signal,
        'composite_momentum_score': composite.composite_momentum_score,
    }

# 延迟构建映射字典
INDICATOR_MAP = None

# 按类别分组的指标映射
INDICATOR_CATEGORIES = {
    'trend': [
        'ema', 'sma', 'macd', 'adx', 'parabolic_sar', 'dema', 
        'tema', 'wma', 'hma', 'vwap', 'ppo', 'trix'
    ],
    'momentum': [
        'rsi', 'cci', 'roc', 'momentum', 'stochastic_kd', 'williams_r',
        'ultimate_oscillator', 'awesome_oscillator', 'mfi', 'stoch_rsi'
    ],
    'volatility': [
        'atr', 'bollinger_bands', 'donchian_channel', 'keltner_channel',
        'volatility', 'natr', 'std_dev'
    ],
    'volume': [
        'obv', 'volume_sma', 'chaikin_money_flow', 'accumulation_distribution',
        'volume_rate_of_change', 'ease_of_movement', 'volume_oscillator'
    ],
    'risk': [
        'sharpe_ratio', 'max_drawdown', 'sortino_ratio', 'calmar_ratio',
        'var', 'cvar', 'beta'
    ],
    'composite': [
        'trend_strength_indicator', 'volatility_breakout', 'support_resistance',
        'ichimoku_cloud', 'pivot_points'
    ]
}

def get_indicator(name: str):
    """
    根据名称获取指标函数
    
    Args:
        name: 指标名称
        
    Returns:
        指标函数对象
        
    Raises:
        KeyError: 如果指标不存在
    """
    global INDICATOR_MAP
    if INDICATOR_MAP is None:
        INDICATOR_MAP = _build_indicator_map()
    
    if name not in INDICATOR_MAP:
        available = list(INDICATOR_MAP.keys())
        raise KeyError(f"指标 '{name}' 不存在。可用指标: {available}")
    
    return INDICATOR_MAP[name]

def list_indicators(category: str = None) -> list:
    """
    列出所有可用指标
    
    Args:
        category: 指标类别 ('trend', 'momentum', 'volatility', 'volume', 'risk', 'composite')
        
    Returns:
        指标名称列表
    """
    global INDICATOR_MAP
    if INDICATOR_MAP is None:
        INDICATOR_MAP = _build_indicator_map()
    
    if category is None:
        return list(INDICATOR_MAP.keys())
    
    if category not in INDICATOR_CATEGORIES:
        available_categories = list(INDICATOR_CATEGORIES.keys())
        raise ValueError(f"类别 '{category}' 不存在。可用类别: {available_categories}")
    
    return INDICATOR_CATEGORIES[category]

# 版本信息
__version__ = "1.0.0"
__author__ = "TradeFan Team"
__email__ = "dev@tradefan.ai"

# 导出的公共接口
__all__ = [
    # 模块
    'trend', 'momentum', 'volatility', 'volume', 'risk', 'composite',
    
    # 工具函数
    'INDICATOR_MAP', 'INDICATOR_CATEGORIES', 'get_indicator', 'list_indicators',
    
    # 版本信息
    '__version__', '__author__', '__email__'
] 