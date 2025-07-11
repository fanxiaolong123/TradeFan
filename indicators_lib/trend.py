"""
趋势分析指标模块
==============

包含各种趋势方向和强度分析的技术指标，如移动平均线、MACD、ADX等。
所有函数支持pandas.Series输入，返回计算结果。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Tuple, Union


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    简单移动平均线 (Simple Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        SMA值序列
    """
    return series.rolling(window=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """
    指数移动平均线 (Exponential Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        EMA值序列
    """
    return series.ewm(span=window, adjust=False).mean()


def dema(series: pd.Series, window: int) -> pd.Series:
    """
    双重指数移动平均线 (Double Exponential Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        DEMA值序列
    """
    ema1 = ema(series, window)
    ema2 = ema(ema1, window)
    return 2 * ema1 - ema2


def tema(series: pd.Series, window: int) -> pd.Series:
    """
    三重指数移动平均线 (Triple Exponential Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        TEMA值序列
    """
    ema1 = ema(series, window)
    ema2 = ema(ema1, window)
    ema3 = ema(ema2, window)
    return 3 * ema1 - 3 * ema2 + ema3


def wma(series: pd.Series, window: int) -> pd.Series:
    """
    加权移动平均线 (Weighted Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        WMA值序列
    """
    weights = np.arange(1, window + 1)
    
    def weighted_mean(x):
        return np.average(x, weights=weights)
    
    return series.rolling(window=window).apply(weighted_mean, raw=True)


def hma(series: pd.Series, window: int) -> pd.Series:
    """
    船体移动平均线 (Hull Moving Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        HMA值序列
    """
    half_period = int(window / 2)
    sqrt_period = int(np.sqrt(window))
    
    wma_half = wma(series, half_period)
    wma_full = wma(series, window)
    
    raw_hma = 2 * wma_half - wma_full
    return wma(raw_hma, sqrt_period)


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    成交量加权平均价格 (Volume Weighted Average Price)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        VWAP值序列
    """
    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum()
    cumulative_pv = (typical_price * volume).cumsum()
    
    return cumulative_pv / cumulative_volume


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    移动平均收敛散度 (Moving Average Convergence Divergence)
    
    Args:
        series: 价格序列
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9
        
    Returns:
        (macd_line, signal_line, histogram) 元组
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def ppo(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    价格振荡器百分比 (Percentage Price Oscillator)
    
    Args:
        series: 价格序列
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9
        
    Returns:
        (ppo_line, signal_line, histogram) 元组
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    
    ppo_line = ((ema_fast - ema_slow) / ema_slow) * 100
    signal_line = ema(ppo_line, signal)
    histogram = ppo_line - signal_line
    
    return ppo_line, signal_line, histogram


def adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    平均方向指数 (Average Directional Index)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认14
        
    Returns:
        (adx, plus_di, minus_di) 元组
    """
    # 计算True Range
    high_low = high - low
    high_close = np.abs(high - close.shift(1))
    low_close = np.abs(low - close.shift(1))
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # 计算方向移动
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # 当plus_dm <= minus_dm时，plus_dm = 0
    plus_dm[plus_dm <= minus_dm] = 0
    # 当minus_dm <= plus_dm时，minus_dm = 0
    minus_dm[minus_dm <= plus_dm] = 0
    
    # 计算平滑的TR和DM
    atr = ema(tr, window)
    plus_dm_smoothed = ema(plus_dm, window)
    minus_dm_smoothed = ema(minus_dm, window)
    
    # 计算DI
    plus_di = 100 * (plus_dm_smoothed / atr)
    minus_di = 100 * (minus_dm_smoothed / atr)
    
    # 计算ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_value = ema(dx, window)
    
    return adx_value, plus_di, minus_di


def parabolic_sar(high: pd.Series, low: pd.Series, af: float = 0.02, max_af: float = 0.2) -> pd.Series:
    """
    抛物转向系统 (Parabolic Stop and Reverse)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        af: 加速因子，默认0.02
        max_af: 最大加速因子，默认0.2
        
    Returns:
        SAR值序列
    """
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    trend = pd.Series(index=high.index, dtype=int)
    ep = pd.Series(index=high.index, dtype=float)
    acceleration = pd.Series(index=high.index, dtype=float)
    
    # 初始化
    sar.iloc[0] = low.iloc[0]
    trend.iloc[0] = 1  # 1为上升趋势，-1为下降趋势
    ep.iloc[0] = high.iloc[0]
    acceleration.iloc[0] = af
    
    for i in range(1, length):
        if trend.iloc[i-1] == 1:  # 上升趋势
            sar.iloc[i] = sar.iloc[i-1] + acceleration.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
            
            if low.iloc[i] <= sar.iloc[i]:
                # 趋势反转
                trend.iloc[i] = -1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = low.iloc[i]
                acceleration.iloc[i] = af
            else:
                trend.iloc[i] = 1
                if high.iloc[i] > ep.iloc[i-1]:
                    ep.iloc[i] = high.iloc[i]
                    acceleration.iloc[i] = min(acceleration.iloc[i-1] + af, max_af)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    acceleration.iloc[i] = acceleration.iloc[i-1]
        else:  # 下降趋势
            sar.iloc[i] = sar.iloc[i-1] + acceleration.iloc[i-1] * (ep.iloc[i-1] - sar.iloc[i-1])
            
            if high.iloc[i] >= sar.iloc[i]:
                # 趋势反转
                trend.iloc[i] = 1
                sar.iloc[i] = ep.iloc[i-1]
                ep.iloc[i] = high.iloc[i]
                acceleration.iloc[i] = af
            else:
                trend.iloc[i] = -1
                if low.iloc[i] < ep.iloc[i-1]:
                    ep.iloc[i] = low.iloc[i]
                    acceleration.iloc[i] = min(acceleration.iloc[i-1] + af, max_af)
                else:
                    ep.iloc[i] = ep.iloc[i-1]
                    acceleration.iloc[i] = acceleration.iloc[i-1]
    
    return sar


def trix(series: pd.Series, window: int = 14) -> pd.Series:
    """
    TRIX指标 (Triple Exponential Average)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认14
        
    Returns:
        TRIX值序列
    """
    ema1 = ema(series, window)
    ema2 = ema(ema1, window)
    ema3 = ema(ema2, window)
    
    trix_value = (ema3 / ema3.shift(1) - 1) * 100
    return trix_value


def aroon(high: pd.Series, low: pd.Series, window: int = 14) -> Tuple[pd.Series, pd.Series]:
    """
    阿隆指标 (Aroon)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        window: 计算窗口期，默认14
        
    Returns:
        (aroon_up, aroon_down) 元组
    """
    def aroon_up_calc(x):
        return ((window - x.argmax()) / window) * 100
    
    def aroon_down_calc(x):
        return ((window - x.argmin()) / window) * 100
    
    aroon_up = high.rolling(window=window + 1).apply(aroon_up_calc, raw=True)
    aroon_down = low.rolling(window=window + 1).apply(aroon_down_calc, raw=True)
    
    return aroon_up, aroon_down


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
               period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    SuperTrend指标
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: ATR计算周期，默认10
        multiplier: ATR乘数，默认3.0
        
    Returns:
        (supertrend, trend) 元组，trend为1表示上升趋势，-1表示下降趋势
    """
    from .volatility import atr
    
    hl2 = (high + low) / 2
    atr_value = atr(high, low, close, period)
    
    upper_band = hl2 + (multiplier * atr_value)
    lower_band = hl2 - (multiplier * atr_value)
    
    # 计算最终上下轨
    final_upper = pd.Series(index=close.index, dtype=float)
    final_lower = pd.Series(index=close.index, dtype=float)
    
    final_upper.iloc[0] = upper_band.iloc[0]
    final_lower.iloc[0] = lower_band.iloc[0]
    
    for i in range(1, len(close)):
        final_upper.iloc[i] = upper_band.iloc[i] if (upper_band.iloc[i] < final_upper.iloc[i-1]) or (close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
        final_lower.iloc[i] = lower_band.iloc[i] if (lower_band.iloc[i] > final_lower.iloc[i-1]) or (close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
    
    # 计算SuperTrend
    supertrend = pd.Series(index=close.index, dtype=float)
    trend = pd.Series(index=close.index, dtype=int)
    
    supertrend.iloc[0] = final_lower.iloc[0]
    trend.iloc[0] = 1
    
    for i in range(1, len(close)):
        if (supertrend.iloc[i-1] == final_upper.iloc[i-1]) and (close.iloc[i] <= final_upper.iloc[i]):
            supertrend.iloc[i] = final_upper.iloc[i]
            trend.iloc[i] = -1
        elif (supertrend.iloc[i-1] == final_upper.iloc[i-1]) and (close.iloc[i] > final_upper.iloc[i]):
            supertrend.iloc[i] = final_lower.iloc[i]
            trend.iloc[i] = 1
        elif (supertrend.iloc[i-1] == final_lower.iloc[i-1]) and (close.iloc[i] >= final_lower.iloc[i]):
            supertrend.iloc[i] = final_lower.iloc[i]
            trend.iloc[i] = 1
        elif (supertrend.iloc[i-1] == final_lower.iloc[i-1]) and (close.iloc[i] < final_lower.iloc[i]):
            supertrend.iloc[i] = final_upper.iloc[i]
            trend.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            trend.iloc[i] = trend.iloc[i-1]
    
    return supertrend, trend


# 导出的函数列表
__all__ = [
    'sma', 'ema', 'dema', 'tema', 'wma', 'hma', 'vwap',
    'macd', 'ppo', 'adx', 'parabolic_sar', 'trix', 'aroon', 'supertrend'
] 