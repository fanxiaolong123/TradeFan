"""
成交量分析指标模块
================

包含各种成交量和资金流指标，如OBV、CMF等。
用于分析成交量与价格的关系。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Tuple


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    能量潮指标 (On-Balance Volume)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        OBV值序列
    """
    price_change = close.diff()
    obv_values = pd.Series(index=close.index, dtype=float)
    obv_values.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if price_change.iloc[i] > 0:
            obv_values.iloc[i] = obv_values.iloc[i-1] + volume.iloc[i]
        elif price_change.iloc[i] < 0:
            obv_values.iloc[i] = obv_values.iloc[i-1] - volume.iloc[i]
        else:
            obv_values.iloc[i] = obv_values.iloc[i-1]
    
    return obv_values


def volume_sma(volume: pd.Series, window: int = 20) -> pd.Series:
    """
    成交量简单移动平均 (Volume Simple Moving Average)
    
    Args:
        volume: 成交量序列
        window: 计算窗口期，默认20
        
    Returns:
        成交量SMA序列
    """
    return volume.rolling(window=window).mean()


def chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, 
                      volume: pd.Series, window: int = 20) -> pd.Series:
    """
    蔡金资金流量 (Chaikin Money Flow)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        window: 计算窗口期，默认20
        
    Returns:
        CMF值序列
    """
    # 计算资金流乘数
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    
    # 处理分母为0的情况
    mf_multiplier = mf_multiplier.fillna(0)
    
    # 计算资金流量
    mf_volume = mf_multiplier * volume
    
    # 计算CMF
    cmf = mf_volume.rolling(window=window).sum() / volume.rolling(window=window).sum()
    
    return cmf


def accumulation_distribution(high: pd.Series, low: pd.Series, close: pd.Series, 
                             volume: pd.Series) -> pd.Series:
    """
    累积分布线 (Accumulation/Distribution Line)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        A/D Line值序列
    """
    # 计算资金流乘数
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    
    # 处理分母为0的情况
    mf_multiplier = mf_multiplier.fillna(0)
    
    # 计算资金流量
    mf_volume = mf_multiplier * volume
    
    # 计算累积分布线
    ad_line = mf_volume.cumsum()
    
    return ad_line


def volume_rate_of_change(volume: pd.Series, window: int = 12) -> pd.Series:
    """
    成交量变化率 (Volume Rate of Change)
    
    Args:
        volume: 成交量序列
        window: 计算窗口期，默认12
        
    Returns:
        成交量ROC序列
    """
    volume_roc = ((volume - volume.shift(window)) / volume.shift(window)) * 100
    return volume_roc


def ease_of_movement(high: pd.Series, low: pd.Series, volume: pd.Series, 
                    window: int = 14) -> pd.Series:
    """
    简易波动指标 (Ease of Movement)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        volume: 成交量序列
        window: 移动平均窗口期，默认14
        
    Returns:
        EOM值序列
    """
    # 计算距离移动
    high_low_avg = (high + low) / 2
    distance_moved = high_low_avg.diff()
    
    # 计算高低价差和成交量的比率
    high_low_range = high - low
    box_ratio = volume / 100000000 / high_low_range  # 标准化处理
    
    # 计算1期EMV
    emv_1_period = distance_moved / box_ratio
    
    # 计算EMV移动平均
    emv = emv_1_period.rolling(window=window).mean()
    
    return emv


def volume_oscillator(volume: pd.Series, short_window: int = 5, 
                     long_window: int = 10) -> pd.Series:
    """
    成交量震荡器 (Volume Oscillator)
    
    Args:
        volume: 成交量序列
        short_window: 短期移动平均窗口，默认5
        long_window: 长期移动平均窗口，默认10
        
    Returns:
        成交量震荡器值序列
    """
    short_ma = volume.rolling(window=short_window).mean()
    long_ma = volume.rolling(window=long_window).mean()
    
    vo = ((short_ma - long_ma) / long_ma) * 100
    
    return vo


def price_volume_trend(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    价量趋势 (Price Volume Trend)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        PVT值序列
    """
    price_change_pct = close.pct_change()
    pvt = (price_change_pct * volume).cumsum()
    
    return pvt


def negative_volume_index(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    负成交量指数 (Negative Volume Index)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        NVI值序列
    """
    nvi = pd.Series(index=close.index, dtype=float)
    nvi.iloc[0] = 1000  # 起始值
    
    for i in range(1, len(close)):
        if volume.iloc[i] < volume.iloc[i-1]:
            # 成交量减少时更新NVI
            price_change_pct = (close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1]
            nvi.iloc[i] = nvi.iloc[i-1] * (1 + price_change_pct)
        else:
            # 成交量未减少时保持不变
            nvi.iloc[i] = nvi.iloc[i-1]
    
    return nvi


def positive_volume_index(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    正成交量指数 (Positive Volume Index)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        
    Returns:
        PVI值序列
    """
    pvi = pd.Series(index=close.index, dtype=float)
    pvi.iloc[0] = 1000  # 起始值
    
    for i in range(1, len(close)):
        if volume.iloc[i] > volume.iloc[i-1]:
            # 成交量增加时更新PVI
            price_change_pct = (close.iloc[i] - close.iloc[i-1]) / close.iloc[i-1]
            pvi.iloc[i] = pvi.iloc[i-1] * (1 + price_change_pct)
        else:
            # 成交量未增加时保持不变
            pvi.iloc[i] = pvi.iloc[i-1]
    
    return pvi


def volume_weighted_moving_average(close: pd.Series, volume: pd.Series, 
                                  window: int = 20) -> pd.Series:
    """
    成交量加权移动平均 (Volume Weighted Moving Average)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        window: 计算窗口期，默认20
        
    Returns:
        VWMA值序列
    """
    weighted_price = close * volume
    vwma = weighted_price.rolling(window=window).sum() / volume.rolling(window=window).sum()
    
    return vwma


def klinger_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, 
                      volume: pd.Series, fast_period: int = 34, 
                      slow_period: int = 55, signal_period: int = 13) -> Tuple[pd.Series, pd.Series]:
    """
    克林格震荡器 (Klinger Oscillator)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        volume: 成交量序列
        fast_period: 快速EMA周期，默认34
        slow_period: 慢速EMA周期，默认55
        signal_period: 信号线周期，默认13
        
    Returns:
        (klinger_osc, signal_line) 元组
    """
    # 计算典型价格
    typical_price = (high + low + close) / 3
    
    # 计算趋势方向
    trend = pd.Series(index=close.index, dtype=int)
    for i in range(1, len(typical_price)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            trend.iloc[i] = 1
        else:
            trend.iloc[i] = -1
    trend.iloc[0] = 1
    
    # 计算成交量力度
    volume_force = volume * trend * np.abs((high - low) / ((high + low) / 2))
    
    # 计算快速和慢速EMA
    fast_ema = volume_force.ewm(span=fast_period).mean()
    slow_ema = volume_force.ewm(span=slow_period).mean()
    
    # 计算克林格震荡器
    klinger_osc = fast_ema - slow_ema
    
    # 计算信号线
    signal_line = klinger_osc.ewm(span=signal_period).mean()
    
    return klinger_osc, signal_line


def force_index(close: pd.Series, volume: pd.Series, window: int = 13) -> pd.Series:
    """
    强力指数 (Force Index)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        window: EMA窗口期，默认13
        
    Returns:
        强力指数序列
    """
    price_change = close.diff()
    raw_force_index = price_change * volume
    
    # 计算EMA平滑
    force_idx = raw_force_index.ewm(span=window).mean()
    
    return force_idx


def volume_profile_support_resistance(close: pd.Series, volume: pd.Series, 
                                     window: int = 20, bins: int = 10) -> Tuple[pd.Series, pd.Series]:
    """
    基于成交量的支撑阻力位 (Volume Profile Support/Resistance)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        window: 计算窗口期，默认20
        bins: 价格区间数量，默认10
        
    Returns:
        (support_levels, resistance_levels) 元组
    """
    support_levels = pd.Series(index=close.index, dtype=float)
    resistance_levels = pd.Series(index=close.index, dtype=float)
    
    for i in range(window, len(close)):
        # 获取窗口内数据
        window_close = close.iloc[i-window:i]
        window_volume = volume.iloc[i-window:i]
        
        # 创建价格区间
        price_min = window_close.min()
        price_max = window_close.max()
        price_bins = np.linspace(price_min, price_max, bins + 1)
        
        # 计算每个价格区间的成交量
        volume_by_price = np.zeros(bins)
        for j in range(len(window_close)):
            bin_idx = np.digitize(window_close.iloc[j], price_bins) - 1
            if 0 <= bin_idx < bins:
                volume_by_price[bin_idx] += window_volume.iloc[j]
        
        # 找到成交量最大的价格区间作为支撑/阻力
        max_volume_idx = np.argmax(volume_by_price)
        max_volume_price = (price_bins[max_volume_idx] + price_bins[max_volume_idx + 1]) / 2
        
        # 根据当前价格位置判断支撑还是阻力
        if close.iloc[i] > max_volume_price:
            support_levels.iloc[i] = max_volume_price
            resistance_levels.iloc[i] = np.nan
        else:
            support_levels.iloc[i] = np.nan
            resistance_levels.iloc[i] = max_volume_price
    
    return support_levels, resistance_levels


# 导出的函数列表
__all__ = [
    'obv', 'volume_sma', 'chaikin_money_flow', 'accumulation_distribution',
    'volume_rate_of_change', 'ease_of_movement', 'volume_oscillator',
    'price_volume_trend', 'negative_volume_index', 'positive_volume_index',
    'volume_weighted_moving_average', 'klinger_oscillator', 'force_index',
    'volume_profile_support_resistance'
] 