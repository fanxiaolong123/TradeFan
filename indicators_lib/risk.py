"""
风险评估指标模块
==============

包含各种风险和收益评估指标，如夏普比率、最大回撤、VaR等。
用于评估策略和投资组合的风险收益特征。

Author: TradeFan Team
"""

import pandas as pd
import numpy as np
from typing import Optional


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods: int = 252) -> float:
    """
    夏普比率 (Sharpe Ratio)
    
    Args:
        returns: 收益率序列 (小数形式，如0.01表示1%)
        risk_free_rate: 无风险利率 (年化)，默认0
        periods: 年化周期数，默认252 (交易日)
        
    Returns:
        夏普比率值
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    # 计算年化收益率
    annual_return = returns.mean() * periods
    
    # 计算年化波动率
    annual_volatility = returns.std() * np.sqrt(periods)
    
    # 计算夏普比率
    sharpe = (annual_return - risk_free_rate) / annual_volatility
    
    return float(sharpe)


def sortino_ratio(returns: pd.Series, target_return: float = 0.0, periods: int = 252) -> float:
    """
    索提诺比率 (Sortino Ratio)
    
    Args:
        returns: 收益率序列
        target_return: 目标收益率 (年化)，默认0
        periods: 年化周期数，默认252
        
    Returns:
        索提诺比率值
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算年化收益率
    annual_return = returns.mean() * periods
    
    # 计算下行偏差 (只考虑负收益的波动)
    downside_returns = returns[returns < target_return / periods]
    if len(downside_returns) == 0:
        return float('inf')
    
    downside_deviation = downside_returns.std() * np.sqrt(periods)
    
    if downside_deviation == 0:
        return float('inf')
    
    # 计算索提诺比率
    sortino = (annual_return - target_return) / downside_deviation
    
    return float(sortino)


def max_drawdown(net_value_series: pd.Series) -> float:
    """
    最大回撤 (Maximum Drawdown)
    
    Args:
        net_value_series: 净值序列
        
    Returns:
        最大回撤比例 (正数)
    """
    if len(net_value_series) == 0:
        return 0.0
    
    # 计算累积最高点
    peak = net_value_series.expanding().max()
    
    # 计算回撤
    drawdown = (net_value_series - peak) / peak
    
    # 返回最大回撤 (取正值)
    max_dd = -drawdown.min()
    
    return float(max_dd)


def calmar_ratio(returns: pd.Series, periods: int = 252) -> float:
    """
    卡玛比率 (Calmar Ratio)
    
    Args:
        returns: 收益率序列
        periods: 年化周期数，默认252
        
    Returns:
        卡玛比率值
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算年化收益率
    annual_return = returns.mean() * periods
    
    # 计算净值序列
    net_value = (1 + returns).cumprod()
    
    # 计算最大回撤
    max_dd = max_drawdown(net_value)
    
    if max_dd == 0:
        return float('inf')
    
    # 计算卡玛比率
    calmar = annual_return / max_dd
    
    return float(calmar)


def var(returns: pd.Series, confidence_level: float = 0.05) -> float:
    """
    风险价值 (Value at Risk)
    
    Args:
        returns: 收益率序列
        confidence_level: 置信水平，默认0.05 (5%)
        
    Returns:
        VaR值 (正数表示损失)
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算分位数
    var_value = -returns.quantile(confidence_level)
    
    return float(var_value)


def cvar(returns: pd.Series, confidence_level: float = 0.05) -> float:
    """
    条件风险价值 (Conditional Value at Risk / Expected Shortfall)
    
    Args:
        returns: 收益率序列
        confidence_level: 置信水平，默认0.05 (5%)
        
    Returns:
        CVaR值 (正数表示损失)
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算VaR
    var_value = var(returns, confidence_level)
    
    # 计算超过VaR的损失的平均值
    tail_losses = -returns[returns <= -var_value]
    
    if len(tail_losses) == 0:
        return var_value
    
    cvar_value = tail_losses.mean()
    
    return float(cvar_value)


def beta(returns: pd.Series, market_returns: pd.Series) -> float:
    """
    贝塔系数 (Beta)
    
    Args:
        returns: 资产收益率序列
        market_returns: 市场收益率序列
        
    Returns:
        贝塔值
    """
    if len(returns) == 0 or len(market_returns) == 0:
        return 0.0
    
    # 确保两个序列长度一致
    common_index = returns.index.intersection(market_returns.index)
    if len(common_index) == 0:
        return 0.0
    
    returns_aligned = returns.loc[common_index]
    market_aligned = market_returns.loc[common_index]
    
    # 计算协方差和方差
    covariance = np.cov(returns_aligned, market_aligned)[0, 1]
    market_variance = market_aligned.var()
    
    if market_variance == 0:
        return 0.0
    
    beta_value = covariance / market_variance
    
    return float(beta_value)


def alpha(returns: pd.Series, market_returns: pd.Series, risk_free_rate: float = 0.0, 
          periods: int = 252) -> float:
    """
    阿尔法系数 (Alpha)
    
    Args:
        returns: 资产收益率序列
        market_returns: 市场收益率序列
        risk_free_rate: 无风险利率 (年化)
        periods: 年化周期数
        
    Returns:
        阿尔法值 (年化)
    """
    if len(returns) == 0 or len(market_returns) == 0:
        return 0.0
    
    # 计算贝塔
    beta_value = beta(returns, market_returns)
    
    # 计算年化收益率
    asset_return = returns.mean() * periods
    market_return = market_returns.mean() * periods
    
    # 计算阿尔法
    alpha_value = asset_return - (risk_free_rate + beta_value * (market_return - risk_free_rate))
    
    return float(alpha_value)


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    信息比率 (Information Ratio)
    
    Args:
        returns: 资产收益率序列
        benchmark_returns: 基准收益率序列
        
    Returns:
        信息比率值
    """
    if len(returns) == 0 or len(benchmark_returns) == 0:
        return 0.0
    
    # 确保两个序列长度一致
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) == 0:
        return 0.0
    
    returns_aligned = returns.loc[common_index]
    benchmark_aligned = benchmark_returns.loc[common_index]
    
    # 计算超额收益
    excess_returns = returns_aligned - benchmark_aligned
    
    if len(excess_returns) == 0 or excess_returns.std() == 0:
        return 0.0
    
    # 计算信息比率
    info_ratio = excess_returns.mean() / excess_returns.std()
    
    return float(info_ratio)


def tracking_error(returns: pd.Series, benchmark_returns: pd.Series, periods: int = 252) -> float:
    """
    跟踪误差 (Tracking Error)
    
    Args:
        returns: 资产收益率序列
        benchmark_returns: 基准收益率序列
        periods: 年化周期数
        
    Returns:
        跟踪误差值 (年化)
    """
    if len(returns) == 0 or len(benchmark_returns) == 0:
        return 0.0
    
    # 确保两个序列长度一致
    common_index = returns.index.intersection(benchmark_returns.index)
    if len(common_index) == 0:
        return 0.0
    
    returns_aligned = returns.loc[common_index]
    benchmark_aligned = benchmark_returns.loc[common_index]
    
    # 计算超额收益
    excess_returns = returns_aligned - benchmark_aligned
    
    # 计算年化跟踪误差
    tracking_err = excess_returns.std() * np.sqrt(periods)
    
    return float(tracking_err)


def omega_ratio(returns: pd.Series, target_return: float = 0.0) -> float:
    """
    欧米茄比率 (Omega Ratio)
    
    Args:
        returns: 收益率序列
        target_return: 目标收益率
        
    Returns:
        欧米茄比率值
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算超过目标收益的部分
    upside = returns[returns > target_return] - target_return
    downside = target_return - returns[returns < target_return]
    
    upside_sum = upside.sum() if len(upside) > 0 else 0
    downside_sum = downside.sum() if len(downside) > 0 else 0
    
    if downside_sum == 0:
        return float('inf')
    
    omega = upside_sum / downside_sum
    
    return float(omega)


def pain_index(net_value_series: pd.Series) -> float:
    """
    疼痛指数 (Pain Index)
    
    Args:
        net_value_series: 净值序列
        
    Returns:
        疼痛指数值
    """
    if len(net_value_series) == 0:
        return 0.0
    
    # 计算累积最高点
    peak = net_value_series.expanding().max()
    
    # 计算回撤序列
    drawdown = (peak - net_value_series) / peak
    
    # 计算疼痛指数 (平均回撤)
    pain_idx = drawdown.mean()
    
    return float(pain_idx)


def ulcer_index(net_value_series: pd.Series, window: Optional[int] = None) -> float:
    """
    溃疡指数 (Ulcer Index)
    
    Args:
        net_value_series: 净值序列
        window: 计算窗口，None表示使用全部数据
        
    Returns:
        溃疡指数值
    """
    if len(net_value_series) == 0:
        return 0.0
    
    if window is None:
        # 使用全部数据
        peak = net_value_series.expanding().max()
    else:
        # 使用滚动窗口
        peak = net_value_series.rolling(window=window, min_periods=1).max()
    
    # 计算回撤百分比
    drawdown_pct = ((net_value_series - peak) / peak) * 100
    
    # 计算溃疡指数
    ui = np.sqrt((drawdown_pct ** 2).mean())
    
    return float(ui)


def downside_risk(returns: pd.Series, target_return: float = 0.0, periods: int = 252) -> float:
    """
    下行风险 (Downside Risk)
    
    Args:
        returns: 收益率序列
        target_return: 目标收益率 (年化)
        periods: 年化周期数
        
    Returns:
        下行风险值 (年化)
    """
    if len(returns) == 0:
        return 0.0
    
    # 计算低于目标收益的部分
    target_daily = target_return / periods
    downside_returns = returns[returns < target_daily] - target_daily
    
    if len(downside_returns) == 0:
        return 0.0
    
    # 计算下行风险
    downside_risk_value = np.sqrt((downside_returns ** 2).mean()) * np.sqrt(periods)
    
    return float(downside_risk_value)


# 导出的函数列表
__all__ = [
    'sharpe_ratio', 'sortino_ratio', 'max_drawdown', 'calmar_ratio',
    'var', 'cvar', 'beta', 'alpha', 'information_ratio', 'tracking_error',
    'omega_ratio', 'pain_index', 'ulcer_index', 'downside_risk'
] 