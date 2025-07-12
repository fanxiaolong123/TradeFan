"""
TradeFan 指标库 - 策略工程工具包
包含丰富的技术分析指标，支持策略开发和回测

使用示例:
    from indicators_lib import trend, momentum, volatility, volume, risk, composite
    
    # 计算EMA
    df["ema_fast"] = trend.ema(df["close"], 12)
    
    # 计算RSI
    df["rsi"] = momentum.rsi(df["close"], 14)
    
    # 计算布林带
    df["bb_upper"], df["bb_lower"] = volatility.bollinger_bands(df["close"])
"""

# 导入所有模块
from . import trend
from . import momentum
from . import volatility
from . import volume
from . import risk
from . import composite

# 版本信息
__version__ = "1.0.0"
__author__ = "TradeFan Team"

# 指标映射字典 - 用于动态调用
INDICATOR_MAP = {
    # 趋势指标
    "sma": trend.sma,
    "ema": trend.ema,
    "macd": trend.macd,
    "adx": trend.adx,
    "parabolic_sar": trend.parabolic_sar,
    
    # 动量指标
    "rsi": momentum.rsi,
    "cci": momentum.cci,
    "roc": momentum.roc,
    "momentum": momentum.momentum,
    "stochastic_kd": momentum.stochastic_kd,
    "williams_r": momentum.williams_r,
    
    # 波动率指标
    "atr": volatility.atr,
    "bollinger_bands": volatility.bollinger_bands,
    "donchian_channel": volatility.donchian_channel,
    "keltner_channel": volatility.keltner_channel,
    
    # 成交量指标
    "obv": volume.obv,
    "volume_sma": volume.volume_sma,
    "chaikin_money_flow": volume.chaikin_money_flow,
    "volume_rate_of_change": volume.volume_rate_of_change,
    "accumulation_distribution": volume.accumulation_distribution,
    
    # 风险指标
    "sharpe_ratio": risk.sharpe_ratio,
    "max_drawdown": risk.max_drawdown,
    "sortino_ratio": risk.sortino_ratio,
    "calmar_ratio": risk.calmar_ratio,
    "beta": risk.beta,
    
    # 组合指标
    "trend_strength_indicator": composite.trend_strength_indicator,
    "volatility_breakout": composite.volatility_breakout,
    "momentum_oscillator": composite.momentum_oscillator,
    "support_resistance": composite.support_resistance,
}

# 指标分类
TREND_INDICATORS = ["sma", "ema", "macd", "adx", "parabolic_sar"]
MOMENTUM_INDICATORS = ["rsi", "cci", "roc", "momentum", "stochastic_kd", "williams_r"]
VOLATILITY_INDICATORS = ["atr", "bollinger_bands", "donchian_channel", "keltner_channel"]
VOLUME_INDICATORS = ["obv", "volume_sma", "chaikin_money_flow", "volume_rate_of_change", "accumulation_distribution"]
RISK_INDICATORS = ["sharpe_ratio", "max_drawdown", "sortino_ratio", "calmar_ratio", "beta"]
COMPOSITE_INDICATORS = ["trend_strength_indicator", "volatility_breakout", "momentum_oscillator", "support_resistance"]

ALL_INDICATORS = (TREND_INDICATORS + MOMENTUM_INDICATORS + VOLATILITY_INDICATORS + 
                 VOLUME_INDICATORS + RISK_INDICATORS + COMPOSITE_INDICATORS)

def get_indicator(name: str):
    """
    根据名称获取指标函数
    
    Args:
        name: 指标名称
        
    Returns:
        指标函数
        
    Example:
        rsi_func = get_indicator("rsi")
        rsi_values = rsi_func(close_prices, 14)
    """
    if name in INDICATOR_MAP:
        return INDICATOR_MAP[name]
    else:
        raise ValueError(f"Unknown indicator: {name}. Available indicators: {list(INDICATOR_MAP.keys())}")

def list_indicators(category: str = None):
    """
    列出可用的指标
    
    Args:
        category: 指标类别 ("trend", "momentum", "volatility", "volume", "risk", "composite")
        
    Returns:
        指标名称列表
    """
    if category is None:
        return ALL_INDICATORS
    
    category_map = {
        "trend": TREND_INDICATORS,
        "momentum": MOMENTUM_INDICATORS,
        "volatility": VOLATILITY_INDICATORS,
        "volume": VOLUME_INDICATORS,
        "risk": RISK_INDICATORS,
        "composite": COMPOSITE_INDICATORS
    }
    
    if category in category_map:
        return category_map[category]
    else:
        raise ValueError(f"Unknown category: {category}. Available categories: {list(category_map.keys())}")

# 导出的公共接口
__all__ = [
    # 模块
    "trend", "momentum", "volatility", "volume", "risk", "composite",
    
    # 工具函数
    "get_indicator", "list_indicators",
    
    # 常量
    "INDICATOR_MAP", "ALL_INDICATORS", 
    "TREND_INDICATORS", "MOMENTUM_INDICATORS", "VOLATILITY_INDICATORS",
    "VOLUME_INDICATORS", "RISK_INDICATORS", "COMPOSITE_INDICATORS"
]
