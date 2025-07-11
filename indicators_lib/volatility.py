"""
波动性分析指标模块
================

包含各种波动性和价格区间指标，如ATR、布林带、唐奇安通道等。
用于衡量市场波动性和价格区间。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Tuple


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    平均真实区间 (Average True Range)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认14
        
    Returns:
        ATR值序列
    """
    # 计算True Range
    high_low = high - low
    high_close = np.abs(high - close.shift(1))
    low_close = np.abs(low - close.shift(1))
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_value = true_range.rolling(window=window).mean()
    
    return atr_value


def natr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    标准化平均真实区间 (Normalized Average True Range)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认14
        
    Returns:
        NATR值序列 (百分比)
    """
    atr_value = atr(high, low, close, window)
    natr_value = (atr_value / close) * 100
    
    return natr_value


def bollinger_bands(series: pd.Series, window: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    布林带 (Bollinger Bands)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认20
        std: 标准差倍数，默认2.0
        
    Returns:
        (upper_band, middle_band, lower_band) 元组
    """
    middle_band = series.rolling(window=window).mean()
    std_dev = series.rolling(window=window).std()
    
    upper_band = middle_band + (std_dev * std)
    lower_band = middle_band - (std_dev * std)
    
    return upper_band, middle_band, lower_band


def donchian_channel(high: pd.Series, low: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    唐奇安通道 (Donchian Channel)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        window: 计算窗口期，默认20
        
    Returns:
        (upper_channel, lower_channel) 元组
    """
    upper_channel = high.rolling(window=window).max()
    lower_channel = low.rolling(window=window).min()
    
    return upper_channel, lower_channel


def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series, 
                    window: int = 20, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    肯特纳通道 (Keltner Channel)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认20
        multiplier: ATR乘数，默认2.0
        
    Returns:
        (upper_channel, middle_line, lower_channel) 元组
    """
    middle_line = close.ewm(span=window).mean()
    atr_value = atr(high, low, close, window)
    
    upper_channel = middle_line + (atr_value * multiplier)
    lower_channel = middle_line - (atr_value * multiplier)
    
    return upper_channel, middle_line, lower_channel


def volatility(series: pd.Series, window: int = 20) -> pd.Series:
    """
    历史波动率 (Historical Volatility)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认20
        
    Returns:
        波动率序列 (年化百分比)
    """
    log_returns = np.log(series / series.shift(1))
    vol = log_returns.rolling(window=window).std() * np.sqrt(252) * 100
    
    return vol


def std_dev(series: pd.Series, window: int = 20) -> pd.Series:
    """
    标准差 (Standard Deviation)
    
    Args:
        series: 价格序列
        window: 计算窗口期，默认20
        
    Returns:
        标准差序列
    """
    return series.rolling(window=window).std()


def price_channels(high: pd.Series, low: pd.Series, close: pd.Series, 
                   window: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    价格通道 (Price Channels)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认20
        
    Returns:
        (upper_channel, middle_line, lower_channel) 元组
    """
    upper_channel = high.rolling(window=window).max()
    lower_channel = low.rolling(window=window).min()
    middle_line = (upper_channel + lower_channel) / 2
    
    return upper_channel, middle_line, lower_channel


def ulcer_index(close: pd.Series, window: int = 14) -> pd.Series:
    """
    溃疡指数 (Ulcer Index) - 衡量回撤深度的波动性指标
    
    Args:
        close: 收盘价序列
        window: 计算窗口期，默认14
        
    Returns:
        溃疡指数序列
    """
    # 计算滚动最高价
    rolling_max = close.rolling(window=window, min_periods=1).max()
    
    # 计算回撤百分比
    drawdown_pct = ((close - rolling_max) / rolling_max) * 100
    
    # 计算溃疡指数
    ui = np.sqrt((drawdown_pct ** 2).rolling(window=window).mean())
    
    return ui


def mass_index(high: pd.Series, low: pd.Series, fast_period: int = 9, 
               slow_period: int = 25) -> pd.Series:
    """
    质量指数 (Mass Index) - 基于区间扩张的波动性指标
    
    Args:
        high: 最高价序列
        low: 最低价序列
        fast_period: 快速EMA周期，默认9
        slow_period: 慢速累积周期，默认25
        
    Returns:
        质量指数序列
    """
    # 计算高低价差
    hl_range = high - low
    
    # 计算EMA
    ema1 = hl_range.ewm(span=fast_period).mean()
    ema2 = ema1.ewm(span=fast_period).mean()
    
    # 计算比率
    ratio = ema1 / ema2
    
    # 计算质量指数
    mass_idx = ratio.rolling(window=slow_period).sum()
    
    return mass_idx


def chaikin_volatility(high: pd.Series, low: pd.Series, window: int = 10, 
                       change_period: int = 10) -> pd.Series:
    """
    蔡金波动率 (Chaikin Volatility)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        window: EMA窗口期，默认10
        change_period: 变化率计算周期，默认10
        
    Returns:
        蔡金波动率序列
    """
    # 计算高低价差的EMA
    hl_range = high - low
    ema_hl = hl_range.ewm(span=window).mean()
    
    # 计算变化率
    chaikin_vol = ((ema_hl - ema_hl.shift(change_period)) / ema_hl.shift(change_period)) * 100
    
    return chaikin_vol


def relative_volatility_index(close: pd.Series, window: int = 14, 
                             vol_window: int = 10) -> pd.Series:
    """
    相对波动率指数 (Relative Volatility Index)
    
    Args:
        close: 收盘价序列
        window: RSI计算窗口，默认14
        vol_window: 波动率计算窗口，默认10
        
    Returns:
        RVI值序列
    """
    # 计算价格变化的标准差作为波动率
    price_change = close.diff()
    volatility_measure = price_change.rolling(window=vol_window).std()
    
    # 计算上升和下降波动率
    up_vol = volatility_measure.where(price_change > 0, 0)
    down_vol = volatility_measure.where(price_change < 0, 0)
    
    # 计算平均上升和下降波动率
    avg_up_vol = up_vol.ewm(span=window).mean()
    avg_down_vol = down_vol.ewm(span=window).mean()
    
    # 计算RVI
    rvi = 100 * avg_up_vol / (avg_up_vol + avg_down_vol)
    
    return rvi


def starc_bands(close: pd.Series, window: int = 15, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    STARC带 (Stoller Average Range Channel)
    
    Args:
        close: 收盘价序列
        window: 移动平均窗口，默认15
        multiplier: ATR乘数，默认2.0
        
    Returns:
        (upper_band, middle_line, lower_band) 元组
    """
    # 使用简化的ATR计算
    high = close  # 简化处理
    low = close
    atr_value = atr(high, low, close, window)
    
    middle_line = close.rolling(window=window).mean()
    upper_band = middle_line + (atr_value * multiplier)
    lower_band = middle_line - (atr_value * multiplier)
    
    return upper_band, middle_line, lower_band


def acceleration_bands(high: pd.Series, low: pd.Series, close: pd.Series, 
                      window: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    加速带 (Acceleration Bands)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认20
        
    Returns:
        (upper_band, middle_line, lower_band) 元组
    """
    # 计算价格的移动平均
    hl_avg = (high + low) / 2
    middle_line = hl_avg.rolling(window=window).mean()
    
    # 计算上下带的因子
    factor = 4 * (high - low) / (high + low)
    
    upper_band = high * (1 + factor)
    lower_band = low * (1 - factor)
    
    return upper_band, middle_line, lower_band


def bollinger_bands_width(series: pd.Series, window: int = 20, std: float = 2.0) -> pd.Series:
    """
    布林带宽度 (Bollinger Bands Width)
    
    Args:
        series: 价格序列
        window: 布林带计算窗口，默认20
        std: 标准差倍数，默认2.0
        
    Returns:
        布林带宽度序列
    """
    upper, middle, lower = bollinger_bands(series, window, std)
    bb_width = (upper - lower) / middle
    
    return bb_width


def bollinger_bands_percent_b(series: pd.Series, window: int = 20, std: float = 2.0) -> pd.Series:
    """
    布林带%B (Bollinger Bands %B)
    
    Args:
        series: 价格序列
        window: 布林带计算窗口，默认20
        std: 标准差倍数，默认2.0
        
    Returns:
        %B值序列
    """
    upper, middle, lower = bollinger_bands(series, window, std)
    percent_b = (series - lower) / (upper - lower)
    
    return percent_b


# 导出的函数列表
__all__ = [
    'atr', 'natr', 'bollinger_bands', 'donchian_channel', 'keltner_channel',
    'volatility', 'std_dev', 'price_channels', 'ulcer_index', 'mass_index',
    'chaikin_volatility', 'relative_volatility_index', 'starc_bands',
    'acceleration_bands', 'bollinger_bands_width', 'bollinger_bands_percent_b'
] 