"""
组合指标模块
============

包含各种复合指标和策略信号，如趋势强度、突破信号、支撑阻力等。
结合多个基础指标生成更复杂的分析信号。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from . import trend, momentum, volatility


def trend_strength_indicator(macd_histogram: pd.Series, adx: pd.Series, 
                           threshold: float = 25) -> pd.Series:
    """
    趋势强度指标 (Trend Strength Indicator)
    
    结合MACD直方图和ADX来评估趋势强度
    
    Args:
        macd_histogram: MACD直方图序列
        adx: ADX值序列
        threshold: ADX阈值，默认25
        
    Returns:
        趋势强度分值序列 (0-100)
    """
    # 标准化MACD直方图 (-1 到 1)
    macd_norm = np.tanh(macd_histogram / macd_histogram.std())
    
    # 标准化ADX (0 到 1)
    adx_norm = np.minimum(adx / 100, 1.0)
    
    # 计算趋势强度 (只有当ADX > threshold时才认为有趋势)
    trend_filter = (adx > threshold).astype(int)
    
    # 组合指标
    trend_strength = (abs(macd_norm) * adx_norm * trend_filter) * 100
    
    return trend_strength


def volatility_breakout(close: pd.Series, upper_band: pd.Series, 
                       lower_band: pd.Series, volume: pd.Series = None) -> pd.Series:
    """
    波动率突破信号 (Volatility Breakout Signal)
    
    Args:
        close: 收盘价序列
        upper_band: 上轨序列
        lower_band: 下轨序列
        volume: 成交量序列 (可选，用于确认突破)
        
    Returns:
        突破信号序列 (1: 向上突破, -1: 向下突破, 0: 无突破)
    """
    signals = pd.Series(0, index=close.index)
    
    # 基本突破信号
    upward_breakout = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))
    downward_breakout = (close < lower_band) & (close.shift(1) >= lower_band.shift(1))
    
    if volume is not None:
        # 成交量确认
        volume_confirm = volume > volume.rolling(window=20).mean()
        upward_breakout = upward_breakout & volume_confirm
        downward_breakout = downward_breakout & volume_confirm
    
    signals[upward_breakout] = 1
    signals[downward_breakout] = -1
    
    return signals


def support_resistance(high: pd.Series, low: pd.Series, close: pd.Series, 
                      window: int = 20, strength: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    支撑阻力位识别 (Support/Resistance Levels)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算窗口期，默认20
        strength: 强度要求，默认3 (需要前后几个点确认)
        
    Returns:
        (support_levels, resistance_levels) 元组
    """
    support_levels = pd.Series(np.nan, index=close.index)
    resistance_levels = pd.Series(np.nan, index=close.index)
    
    for i in range(strength, len(low) - strength):
        # 支撑位：低点在周围是最低的
        is_support = True
        for j in range(i - strength, i + strength + 1):
            if j != i and low.iloc[j] <= low.iloc[i]:
                is_support = False
                break
        
        if is_support:
            support_levels.iloc[i] = low.iloc[i]
        
        # 阻力位：高点在周围是最高的
        is_resistance = True
        for j in range(i - strength, i + strength + 1):
            if j != i and high.iloc[j] >= high.iloc[i]:
                is_resistance = False
                break
        
        if is_resistance:
            resistance_levels.iloc[i] = high.iloc[i]
    
    return support_levels, resistance_levels


def ichimoku_cloud(high: pd.Series, low: pd.Series, close: pd.Series,
                   tenkan_period: int = 9, kijun_period: int = 26, 
                   senkou_period: int = 52) -> Dict[str, pd.Series]:
    """
    一目均衡表 (Ichimoku Cloud)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        tenkan_period: 转换线周期，默认9
        kijun_period: 基准线周期，默认26
        senkou_period: 先行带周期，默认52
        
    Returns:
        包含各条线的字典
    """
    # 转换线 (Tenkan-sen)
    tenkan_sen = (high.rolling(tenkan_period).max() + low.rolling(tenkan_period).min()) / 2
    
    # 基准线 (Kijun-sen)
    kijun_sen = (high.rolling(kijun_period).max() + low.rolling(kijun_period).min()) / 2
    
    # 先行带A (Senkou Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    
    # 先行带B (Senkou Span B)
    senkou_span_b = ((high.rolling(senkou_period).max() + 
                     low.rolling(senkou_period).min()) / 2).shift(kijun_period)
    
    # 滞后线 (Chikou Span)
    chikou_span = close.shift(-kijun_period)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
    """
    枢轴点 (Pivot Points)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        
    Returns:
        包含各个枢轴点的字典
    """
    # 前一日的价格数据
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    
    # 计算枢轴点
    pivot = (prev_high + prev_low + prev_close) / 3
    
    # 支撑位
    support1 = 2 * pivot - prev_high
    support2 = pivot - (prev_high - prev_low)
    support3 = prev_low - 2 * (prev_high - pivot)
    
    # 阻力位
    resistance1 = 2 * pivot - prev_low
    resistance2 = pivot + (prev_high - prev_low)
    resistance3 = prev_high + 2 * (pivot - prev_low)
    
    return {
        'pivot': pivot,
        'support1': support1,
        'support2': support2,
        'support3': support3,
        'resistance1': resistance1,
        'resistance2': resistance2,
        'resistance3': resistance3
    }


def momentum_divergence(price: pd.Series, oscillator: pd.Series, 
                       window: int = 14) -> pd.Series:
    """
    动量背离检测 (Momentum Divergence)
    
    Args:
        price: 价格序列
        oscillator: 震荡器序列 (如RSI、MACD等)
        window: 检测窗口期，默认14
        
    Returns:
        背离信号序列 (1: 看涨背离, -1: 看跌背离, 0: 无背离)
    """
    signals = pd.Series(0, index=price.index)
    
    for i in range(window, len(price)):
        # 获取窗口内数据
        price_window = price.iloc[i-window:i+1]
        osc_window = oscillator.iloc[i-window:i+1]
        
        # 价格趋势
        price_trend = price_window.iloc[-1] - price_window.iloc[0]
        
        # 震荡器趋势
        osc_trend = osc_window.iloc[-1] - osc_window.iloc[0]
        
        # 检测背离
        if price_trend < 0 and osc_trend > 0:  # 看涨背离
            signals.iloc[i] = 1
        elif price_trend > 0 and osc_trend < 0:  # 看跌背离
            signals.iloc[i] = -1
    
    return signals


def multi_timeframe_signal(close: pd.Series, timeframes: List[int] = [5, 20, 50]) -> pd.Series:
    """
    多时间框架信号 (Multi-Timeframe Signal)
    
    Args:
        close: 收盘价序列
        timeframes: 时间框架列表，默认[5, 20, 50]
        
    Returns:
        综合信号强度序列 (-1 到 1)
    """
    signals = pd.DataFrame(index=close.index)
    
    for tf in timeframes:
        # 计算EMA
        ema = trend.ema(close, tf)
        
        # 计算信号 (价格相对于EMA的位置)
        signal = (close - ema) / ema
        signals[f'signal_{tf}'] = signal
    
    # 加权平均 (较短时间框架权重更高)
    weights = [1.0 / tf for tf in timeframes]
    weights = np.array(weights) / sum(weights)
    
    combined_signal = sum(signals[f'signal_{tf}'] * weight 
                         for tf, weight in zip(timeframes, weights))
    
    # 标准化到 -1 到 1 范围
    combined_signal = np.tanh(combined_signal)
    
    return combined_signal


def market_regime_detection(close: pd.Series, volume: pd.Series = None, 
                           window: int = 50) -> pd.Series:
    """
    市场状态检测 (Market Regime Detection)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列 (可选)
        window: 计算窗口期，默认50
        
    Returns:
        市场状态序列 (1: 趋势市场, 0: 震荡市场)
    """
    # 计算价格波动率
    returns = close.pct_change()
    volatility_score = returns.rolling(window).std()
    
    # 计算趋势强度
    price_range = close.rolling(window).max() - close.rolling(window).min()
    trend_strength = abs(close - close.rolling(window).mean()) / price_range
    
    # 计算ADX
    high = close  # 简化处理
    low = close
    adx_value, _, _ = trend.adx(high, low, close, window // 3)
    
    # 综合评分
    regime_score = (trend_strength + adx_value / 100) / 2
    
    # 如果有成交量数据，考虑成交量确认
    if volume is not None:
        volume_trend = volume.rolling(window).mean() / volume.rolling(window * 2).mean()
        regime_score = regime_score * volume_trend
    
    # 二值化 (阈值可调整)
    regime = (regime_score > regime_score.rolling(window * 2).median()).astype(int)
    
    return regime


def fibonacci_retracement(high: pd.Series, low: pd.Series, 
                         levels: List[float] = [0.236, 0.382, 0.5, 0.618, 0.786]) -> Dict[str, pd.Series]:
    """
    斐波那契回撤 (Fibonacci Retracement)
    
    Args:
        high: 最高价序列
        low: 最低价序列
        levels: 回撤水平列表，默认常用比例
        
    Returns:
        包含各回撤水平的字典
    """
    # 计算价格区间
    price_range = high - low
    
    retracement_levels = {}
    
    for level in levels:
        # 向上趋势的回撤
        uptrend_retracement = high - (price_range * level)
        
        # 向下趋势的回撤
        downtrend_retracement = low + (price_range * level)
        
        retracement_levels[f'up_{level}'] = uptrend_retracement
        retracement_levels[f'down_{level}'] = downtrend_retracement
    
    return retracement_levels


def volume_price_analysis(close: pd.Series, volume: pd.Series, 
                         window: int = 20) -> Dict[str, pd.Series]:
    """
    量价分析 (Volume Price Analysis)
    
    Args:
        close: 收盘价序列
        volume: 成交量序列
        window: 计算窗口期，默认20
        
    Returns:
        包含各种量价指标的字典
    """
    # 价格变化
    price_change = close.pct_change()
    
    # 成交量相对强度
    volume_ratio = volume / volume.rolling(window).mean()
    
    # 量价确认信号
    up_volume_confirm = (price_change > 0) & (volume_ratio > 1.2)
    down_volume_confirm = (price_change < 0) & (volume_ratio > 1.2)
    
    # 背离信号
    price_up_volume_down = (price_change > 0) & (volume_ratio < 0.8)
    price_down_volume_up = (price_change < 0) & (volume_ratio > 1.2)
    
    return {
        'volume_ratio': volume_ratio,
        'up_volume_confirm': up_volume_confirm.astype(int),
        'down_volume_confirm': down_volume_confirm.astype(int),
        'price_up_volume_down': price_up_volume_down.astype(int),
        'price_down_volume_up': price_down_volume_up.astype(int)
    }


def composite_momentum_score(close: pd.Series, high: pd.Series, low: pd.Series, 
                           volume: pd.Series) -> pd.Series:
    """
    综合动量评分 (Composite Momentum Score)
    
    结合多个动量指标生成综合评分
    
    Args:
        close: 收盘价序列
        high: 最高价序列
        low: 最低价序列
        volume: 成交量序列
        
    Returns:
        综合动量评分序列 (-100 到 100)
    """
    # RSI评分 (标准化到-1到1)
    rsi = momentum.rsi(close, 14)
    rsi_score = (rsi - 50) / 50
    
    # ROC评分
    roc = momentum.roc(close, 10)
    roc_score = np.tanh(roc / 5)  # 标准化
    
    # 随机指标评分
    k_percent, d_percent = momentum.stochastic_kd(high, low, close, 14, 3)
    stoch_score = (k_percent - 50) / 50
    
    # 威廉指标评分
    williams = momentum.williams_r(high, low, close, 14)
    williams_score = (williams + 50) / 50
    
    # MFI评分 (考虑成交量)
    mfi = momentum.mfi(high, low, close, volume, 14)
    mfi_score = (mfi - 50) / 50
    
    # 加权综合评分
    weights = [0.25, 0.25, 0.2, 0.15, 0.15]
    scores = [rsi_score, roc_score, stoch_score, williams_score, mfi_score]
    
    composite_score = sum(score * weight for score, weight in zip(scores, weights))
    
    # 转换到-100到100范围
    composite_score = composite_score * 100
    
    return composite_score


def momentum_oscillator(rsi: pd.Series, stoch_k: pd.Series, 
                       weights: Tuple[float, float] = (0.6, 0.4)) -> pd.Series:
    """
    动量振荡器 (Momentum Oscillator)
    
    结合RSI和随机指标K值，生成综合动量信号
    
    Args:
        rsi: RSI指标序列
        stoch_k: 随机指标K值序列
        weights: RSI和Stoch权重 (默认: (0.6, 0.4))
        
    Returns:
        pd.Series: 动量振荡器值 (0-100)
        
    Example:
        rsi = momentum.rsi(close, 14)
        stoch_k, _ = momentum.stochastic_kd(high, low, close)
        momentum_osc = momentum_oscillator(rsi, stoch_k)
    """
    try:
        # 标准化到0-100范围
        rsi_norm = rsi.fillna(50)  # RSI默认值50
        stoch_norm = stoch_k.fillna(50)  # Stoch默认值50
        
        # 加权平均
        oscillator = (rsi_norm * weights[0] + stoch_norm * weights[1])
        
        return oscillator.round(2)
        
    except Exception as e:
        print(f"Error calculating momentum oscillator: {e}")
        return pd.Series([50] * len(rsi), index=rsi.index)


# 导出的函数列表
__all__ = [
    'trend_strength_indicator', 'volatility_breakout', 'support_resistance',
    'ichimoku_cloud', 'pivot_points', 'momentum_divergence', 'multi_timeframe_signal',
    'market_regime_detection', 'fibonacci_retracement', 'volume_price_analysis',
    'composite_momentum_score', 'momentum_oscillator'
] 