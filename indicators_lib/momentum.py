"""
动量分析指标模块
==============

包含各种动量和振荡器指标，如RSI、CCI、ROC等。
用于判断价格变化的速度和强度。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Tuple


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    相对强弱指数 (Relative Strength Index)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认14
        
    Returns:
        RSI值序列 (0-100)
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    rs = avg_gain / avg_loss
    rsi_value = 100 - (100 / (1 + rs))
    
    return rsi_value


def stoch_rsi(series: pd.Series, window: int = 14, k_window: int = 3, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    随机RSI (Stochastic RSI)
    
    Args:
        series: 价格序列
        window: RSI计算窗口期，默认14
        k_window: %K平滑周期，默认3
        d_window: %D平滑周期，默认3
        
    Returns:
        (%K, %D) 元组
    """
    rsi_value = rsi(series, window)
    
    lowest_rsi = rsi_value.rolling(window=window).min()
    highest_rsi = rsi_value.rolling(window=window).max()
    
    stoch_rsi_value = (rsi_value - lowest_rsi) / (highest_rsi - lowest_rsi) * 100
    
    k_percent = stoch_rsi_value.rolling(window=k_window).mean()
    d_percent = k_percent.rolling(window=d_window).mean()
    
    return k_percent, d_percent


def cci(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 20) -> pd.Series:
    """
    商品通道指数 (Commodity Channel Index)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认20
        
    Returns:
        CCI值序列
    """
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=window).mean()
    mean_deviation = typical_price.rolling(window=window).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    
    cci_value = (typical_price - sma_tp) / (0.015 * mean_deviation)
    return cci_value


def roc(series: pd.Series, window: int = 12) -> pd.Series:
    """
    变化率 (Rate of Change)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认12
        
    Returns:
        ROC值序列 (百分比)
    """
    roc_value = ((series - series.shift(window)) / series.shift(window)) * 100
    return roc_value


def momentum(series: pd.Series, window: int = 10) -> pd.Series:
    """
    动量指标 (Momentum)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认10
        
    Returns:
        动量值序列
    """
    momentum_value = series - series.shift(window)
    return momentum_value


def stochastic_kd(high: pd.Series, low: pd.Series, close: pd.Series, 
                  k_window: int = 14, d_window: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    随机指标 (Stochastic Oscillator)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        k_window: %K计算窗口期，默认14
        d_window: %D平滑窗口期，默认3
        
    Returns:
        (%K, %D) 元组
    """
    lowest_low = low.rolling(window=k_window).min()
    highest_high = high.rolling(window=k_window).max()
    
    k_percent = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    d_percent = k_percent.rolling(window=d_window).mean()
    
    return k_percent, d_percent


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    威廉指标 (Williams %R)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认14
        
    Returns:
        Williams %R值序列 (-100 到 0)
    """
    highest_high = high.rolling(window=window).max()
    lowest_low = low.rolling(window=window).min()
    
    williams_r_value = ((highest_high - close) / (highest_high - lowest_low)) * -100
    return williams_r_value


def ultimate_oscillator(high: pd.Series, low: pd.Series, close: pd.Series,
                        period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """
    终极振荡器 (Ultimate Oscillator)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period1: 短期周期，默认7
        period2: 中期周期，默认14
        period3: 长期周期，默认28
        
    Returns:
        Ultimate Oscillator值序列 (0-100)
    """
    # 计算True Low和Buying Pressure
    prev_close = close.shift(1)
    true_low = pd.concat([low, prev_close], axis=1).min(axis=1)
    buying_pressure = close - true_low
    
    # 计算True Range
    high_low = high - low
    high_close = np.abs(high - prev_close)
    low_close = np.abs(low - prev_close)
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # 计算各周期的平均值
    bp1 = buying_pressure.rolling(window=period1).sum()
    bp2 = buying_pressure.rolling(window=period2).sum()
    bp3 = buying_pressure.rolling(window=period3).sum()
    
    tr1 = true_range.rolling(window=period1).sum()
    tr2 = true_range.rolling(window=period2).sum()
    tr3 = true_range.rolling(window=period3).sum()
    
    # 计算Ultimate Oscillator
    uo = 100 * ((4 * (bp1 / tr1)) + (2 * (bp2 / tr2)) + (bp3 / tr3)) / 7
    
    return uo


def awesome_oscillator(high: pd.Series, low: pd.Series, 
                      fast_period: int = 5, slow_period: int = 34) -> pd.Series:
    """
    动量振荡器 (Awesome Oscillator)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        fast_period: 快速周期，默认5
        slow_period: 慢速周期，默认34
        
    Returns:
        AO值序列
    """
    median_price = (high + low) / 2
    
    ao_fast = median_price.rolling(window=fast_period).mean()
    ao_slow = median_price.rolling(window=slow_period).mean()
    
    awesome_osc = ao_fast - ao_slow
    return awesome_osc


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, 
        window: int = 14) -> pd.Series:
    """
    资金流量指数 (Money Flow Index)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        window: 计算窗口期，默认14
        
    Returns:
        MFI值序列 (0-100)
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    # 计算价格变化方向
    price_change = typical_price.diff()
    
    # 分离正负资金流
    positive_mf = money_flow.where(price_change > 0, 0)
    negative_mf = money_flow.where(price_change < 0, 0)
    
    # 计算资金流比率
    positive_mf_sum = positive_mf.rolling(window=window).sum()
    negative_mf_sum = negative_mf.rolling(window=window).sum()
    
    money_flow_ratio = positive_mf_sum / negative_mf_sum
    
    # 计算MFI
    mfi_value = 100 - (100 / (1 + money_flow_ratio))
    
    return mfi_value


def tsi(series: pd.Series, long_window: int = 25, short_window: int = 13) -> pd.Series:
    """
    真实强度指数 (True Strength Index)
    
    Args:
        series: 价格序列
        long_window: 长期平滑周期，默认25
        short_window: 短期平滑周期，默认13
        
    Returns:
        TSI值序列
    """
    # 计算价格变化
    price_change = series.diff()
    
    # 双重平滑价格变化
    first_smooth_pc = price_change.ewm(span=long_window).mean()
    double_smooth_pc = first_smooth_pc.ewm(span=short_window).mean()
    
    # 双重平滑绝对价格变化
    abs_price_change = np.abs(price_change)
    first_smooth_apc = abs_price_change.ewm(span=long_window).mean()
    double_smooth_apc = first_smooth_apc.ewm(span=short_window).mean()
    
    # 计算TSI
    tsi_value = 100 * (double_smooth_pc / double_smooth_apc)
    
    return tsi_value


def dpo(series: pd.Series, window: int = 20) -> pd.Series:
    """
    区间振荡器 (Detrended Price Oscillator)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认20
        
    Returns:
        DPO值序列
    """
    # 计算移动平均线
    sma_value = series.rolling(window=window).mean()
    
    # 计算偏移量
    shift_period = int(window / 2) + 1
    
    # 计算DPO
    dpo_value = series - sma_value.shift(shift_period)
    
    return dpo_value


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
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    
    ppo_line = ((ema_fast - ema_slow) / ema_slow) * 100
    signal_line = ppo_line.ewm(span=signal).mean()
    histogram = ppo_line - signal_line
    
    return ppo_line, signal_line, histogram


def kama(series: pd.Series, window: int = 10, fast_sc: int = 2, slow_sc: int = 30) -> pd.Series:
    """
    考夫曼自适应移动平均线 (Kaufman's Adaptive Moving Average)
    
    Args:
        series: 价格序列
        window: 效率比计算窗口，默认10
        fast_sc: 快速平滑常数，默认2
        slow_sc: 慢速平滑常数，默认30
        
    Returns:
        KAMA值序列
    """
    # 计算效率比 (Efficiency Ratio)
    direction = np.abs(series - series.shift(window))
    volatility = np.abs(series.diff()).rolling(window=window).sum()
    er = direction / volatility
    
    # 计算平滑常数
    fastest_sc = 2.0 / (fast_sc + 1.0)
    slowest_sc = 2.0 / (slow_sc + 1.0)
    sc = (er * (fastest_sc - slowest_sc) + slowest_sc) ** 2
    
    # 计算KAMA
    kama_value = pd.Series(index=series.index, dtype=float)
    kama_value.iloc[0] = series.iloc[0]
    
    for i in range(1, len(series)):
        kama_value.iloc[i] = kama_value.iloc[i-1] + sc.iloc[i] * (series.iloc[i] - kama_value.iloc[i-1])
    
    return kama_value


# 导出的函数列表
__all__ = [
    'rsi', 'stoch_rsi', 'cci', 'roc', 'momentum', 'stochastic_kd', 'williams_r',
    'ultimate_oscillator', 'awesome_oscillator', 'mfi', 'tsi', 'dpo', 'ppo', 'kama'
] 