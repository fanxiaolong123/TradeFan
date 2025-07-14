"""
性能指标模块
提供策略和组合的性能分析和评估工具
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .signal import Signal, SignalType


class MetricType(Enum):
    """指标类型枚举"""
    RETURN = "return"           # 收益类指标
    RISK = "risk"              # 风险类指标
    EFFICIENCY = "efficiency"   # 效率类指标
    SIGNAL = "signal"          # 信号类指标


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    name: str
    value: float
    type: MetricType
    description: str
    benchmark: Optional[float] = None
    is_better_higher: bool = True  # True表示数值越高越好


class PerformanceMetrics:
    """
    性能指标计算器
    提供各种策略和组合性能指标的计算
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        初始化性能指标计算器
        
        Args:
            risk_free_rate: 无风险利率，用于计算夏普比率等指标
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_signal_metrics(self, signals: List[Signal]) -> Dict[str, PerformanceMetric]:
        """
        计算信号相关指标
        
        Args:
            signals: 信号列表
            
        Returns:
            信号指标字典
        """
        if not signals:
            return {}
        
        metrics = {}
        
        # 基础信号统计
        total_signals = len(signals)
        buy_signals = sum(1 for s in signals if s.is_buy_signal())
        sell_signals = sum(1 for s in signals if s.is_sell_signal())
        strong_signals = sum(1 for s in signals if s.is_strong_signal())
        
        # 信号频率
        if len(signals) > 1:
            time_span = (signals[-1].timestamp - signals[0].timestamp).total_seconds() / 3600  # 小时
            signal_frequency = total_signals / max(time_span, 1)
        else:
            signal_frequency = 0
        
        # 平均信号强度
        avg_strength = sum(s.strength for s in signals) / total_signals
        
        # 信号分布均衡性
        buy_ratio = buy_signals / total_signals if total_signals > 0 else 0
        sell_ratio = sell_signals / total_signals if total_signals > 0 else 0
        balance_score = 1 - abs(buy_ratio - sell_ratio)  # 越接近1越均衡
        
        # 强信号比例
        strong_signal_ratio = strong_signals / total_signals if total_signals > 0 else 0
        
        # 创建指标对象
        metrics['total_signals'] = PerformanceMetric(
            "总信号数", total_signals, MetricType.SIGNAL, "策略产生的总信号数量"
        )
        
        metrics['signal_frequency'] = PerformanceMetric(
            "信号频率", round(signal_frequency, 2), MetricType.SIGNAL, 
            "每小时产生的信号数量", benchmark=1.0
        )
        
        metrics['avg_signal_strength'] = PerformanceMetric(
            "平均信号强度", round(avg_strength, 3), MetricType.SIGNAL,
            "所有信号的平均强度", benchmark=0.5
        )
        
        metrics['signal_balance'] = PerformanceMetric(
            "信号均衡性", round(balance_score, 3), MetricType.SIGNAL,
            "买卖信号的均衡程度", benchmark=0.8
        )
        
        metrics['strong_signal_ratio'] = PerformanceMetric(
            "强信号比例", round(strong_signal_ratio, 3), MetricType.SIGNAL,
            "强信号占总信号的比例", benchmark=0.3
        )
        
        return metrics
    
    def calculate_return_metrics(self, returns: List[float], 
                               benchmark_returns: Optional[List[float]] = None) -> Dict[str, PerformanceMetric]:
        """
        计算收益相关指标
        
        Args:
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            
        Returns:
            收益指标字典
        """
        if not returns:
            return {}
        
        metrics = {}
        returns_array = np.array(returns)
        
        # 总收益率
        total_return = np.prod(1 + returns_array) - 1
        
        # 年化收益率
        periods_per_year = 252  # 假设日收益率
        if len(returns) > 0:
            annualized_return = (1 + total_return) ** (periods_per_year / len(returns)) - 1
        else:
            annualized_return = 0
        
        # 平均收益率
        avg_return = np.mean(returns_array)
        
        # 收益率标准差
        return_std = np.std(returns_array, ddof=1) if len(returns) > 1 else 0
        
        # 年化波动率
        annualized_volatility = return_std * np.sqrt(periods_per_year)
        
        # 夏普比率
        excess_return = annualized_return - self.risk_free_rate
        sharpe_ratio = excess_return / annualized_volatility if annualized_volatility > 0 else 0
        
        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        # 胜率
        win_rate = np.sum(returns_array > 0) / len(returns_array) if len(returns_array) > 0 else 0
        
        # 盈亏比
        winning_returns = returns_array[returns_array > 0]
        losing_returns = returns_array[returns_array < 0]
        
        if len(winning_returns) > 0 and len(losing_returns) > 0:
            profit_loss_ratio = np.mean(winning_returns) / abs(np.mean(losing_returns))
        else:
            profit_loss_ratio = 0
        
        # 创建指标对象
        metrics['total_return'] = PerformanceMetric(
            "总收益率", round(total_return, 4), MetricType.RETURN,
            "策略的总收益率", benchmark=0.1
        )
        
        metrics['annualized_return'] = PerformanceMetric(
            "年化收益率", round(annualized_return, 4), MetricType.RETURN,
            "年化后的收益率", benchmark=0.15
        )
        
        metrics['sharpe_ratio'] = PerformanceMetric(
            "夏普比率", round(sharpe_ratio, 3), MetricType.EFFICIENCY,
            "风险调整后的收益率", benchmark=1.0
        )
        
        metrics['max_drawdown'] = PerformanceMetric(
            "最大回撤", round(abs(max_drawdown), 4), MetricType.RISK,
            "最大回撤幅度", benchmark=0.1, is_better_higher=False
        )
        
        metrics['volatility'] = PerformanceMetric(
            "年化波动率", round(annualized_volatility, 4), MetricType.RISK,
            "收益率的年化标准差", benchmark=0.2, is_better_higher=False
        )
        
        metrics['win_rate'] = PerformanceMetric(
            "胜率", round(win_rate, 3), MetricType.EFFICIENCY,
            "盈利交易的比例", benchmark=0.5
        )
        
        metrics['profit_loss_ratio'] = PerformanceMetric(
            "盈亏比", round(profit_loss_ratio, 3), MetricType.EFFICIENCY,
            "平均盈利与平均亏损的比值", benchmark=1.5
        )
        
        # 如果有基准收益，计算相对指标
        if benchmark_returns and len(benchmark_returns) == len(returns):
            benchmark_array = np.array(benchmark_returns)
            
            # 信息比率
            excess_returns = returns_array - benchmark_array
            tracking_error = np.std(excess_returns, ddof=1) if len(excess_returns) > 1 else 0
            information_ratio = np.mean(excess_returns) / tracking_error if tracking_error > 0 else 0
            
            # Beta
            if np.var(benchmark_array) > 0:
                beta = np.cov(returns_array, benchmark_array)[0, 1] / np.var(benchmark_array)
            else:
                beta = 0
            
            # Alpha
            benchmark_total_return = np.prod(1 + benchmark_array) - 1
            alpha = total_return - beta * benchmark_total_return
            
            metrics['information_ratio'] = PerformanceMetric(
                "信息比率", round(information_ratio, 3), MetricType.EFFICIENCY,
                "相对基准的超额收益风险比", benchmark=0.5
            )
            
            metrics['beta'] = PerformanceMetric(
                "Beta", round(beta, 3), MetricType.RISK,
                "相对基准的系统性风险", benchmark=1.0, is_better_higher=False
            )
            
            metrics['alpha'] = PerformanceMetric(
                "Alpha", round(alpha, 4), MetricType.RETURN,
                "相对基准的超额收益", benchmark=0.02
            )
        
        return metrics
    
    def calculate_risk_metrics(self, returns: List[float]) -> Dict[str, PerformanceMetric]:
        """
        计算风险相关指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            风险指标字典
        """
        if not returns:
            return {}
        
        metrics = {}
        returns_array = np.array(returns)
        
        # VaR (Value at Risk) - 95%置信度
        var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0
        
        # CVaR (Conditional Value at Risk) - 95%置信度
        cvar_95 = np.mean(returns_array[returns_array <= var_95]) if np.any(returns_array <= var_95) else 0
        
        # 下行偏差
        negative_returns = returns_array[returns_array < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 1 else 0
        
        # Sortino比率
        excess_return = np.mean(returns_array) - self.risk_free_rate / 252  # 日化无风险利率
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
        
        # 最大连续亏损天数
        consecutive_losses = 0
        max_consecutive_losses = 0
        for ret in returns_array:
            if ret < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0
        
        # 创建指标对象
        metrics['var_95'] = PerformanceMetric(
            "VaR(95%)", round(abs(var_95), 4), MetricType.RISK,
            "95%置信度下的最大损失", benchmark=0.02, is_better_higher=False
        )
        
        metrics['cvar_95'] = PerformanceMetric(
            "CVaR(95%)", round(abs(cvar_95), 4), MetricType.RISK,
            "95%置信度下的条件风险价值", benchmark=0.03, is_better_higher=False
        )
        
        metrics['downside_deviation'] = PerformanceMetric(
            "下行偏差", round(downside_deviation, 4), MetricType.RISK,
            "负收益的标准差", benchmark=0.02, is_better_higher=False
        )
        
        metrics['sortino_ratio'] = PerformanceMetric(
            "Sortino比率", round(sortino_ratio, 3), MetricType.EFFICIENCY,
            "下行风险调整后的收益率", benchmark=1.5
        )
        
        metrics['max_consecutive_losses'] = PerformanceMetric(
            "最大连续亏损", max_consecutive_losses, MetricType.RISK,
            "最大连续亏损天数", benchmark=5, is_better_higher=False
        )
        
        return metrics
    
    def calculate_comprehensive_metrics(self, signals: List[Signal], 
                                      returns: Optional[List[float]] = None,
                                      benchmark_returns: Optional[List[float]] = None) -> Dict[str, PerformanceMetric]:
        """
        计算综合性能指标
        
        Args:
            signals: 信号列表
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            
        Returns:
            综合指标字典
        """
        all_metrics = {}
        
        # 信号指标
        signal_metrics = self.calculate_signal_metrics(signals)
        all_metrics.update(signal_metrics)
        
        # 收益和风险指标
        if returns:
            return_metrics = self.calculate_return_metrics(returns, benchmark_returns)
            risk_metrics = self.calculate_risk_metrics(returns)
            
            all_metrics.update(return_metrics)
            all_metrics.update(risk_metrics)
        
        return all_metrics
    
    def generate_performance_report(self, metrics: Dict[str, PerformanceMetric]) -> Dict[str, Any]:
        """
        生成性能报告
        
        Args:
            metrics: 性能指标字典
            
        Returns:
            格式化的性能报告
        """
        report = {
            'summary': {},
            'details': {},
            'warnings': [],
            'recommendations': []
        }
        
        # 按类型分组指标
        by_type = {}
        for name, metric in metrics.items():
            metric_type = metric.type.value
            if metric_type not in by_type:
                by_type[metric_type] = {}
            by_type[metric_type][name] = metric
        
        # 生成摘要
        for metric_type, type_metrics in by_type.items():
            report['summary'][metric_type] = {
                name: {
                    'value': metric.value,
                    'benchmark': metric.benchmark,
                    'status': self._evaluate_metric(metric)
                }
                for name, metric in type_metrics.items()
            }
        
        # 生成详细信息
        for name, metric in metrics.items():
            report['details'][name] = {
                'name': metric.name,
                'value': metric.value,
                'type': metric.type.value,
                'description': metric.description,
                'benchmark': metric.benchmark,
                'is_better_higher': metric.is_better_higher,
                'status': self._evaluate_metric(metric),
                'score': self._calculate_metric_score(metric)
            }
        
        # 生成警告和建议
        report['warnings'] = self._generate_warnings(metrics)
        report['recommendations'] = self._generate_recommendations(metrics)
        
        return report
    
    def _evaluate_metric(self, metric: PerformanceMetric) -> str:
        """评估指标状态"""
        if metric.benchmark is None:
            return "无基准"
        
        if metric.is_better_higher:
            if metric.value >= metric.benchmark * 1.2:
                return "优秀"
            elif metric.value >= metric.benchmark:
                return "良好"
            elif metric.value >= metric.benchmark * 0.8:
                return "一般"
            else:
                return "较差"
        else:
            if metric.value <= metric.benchmark * 0.8:
                return "优秀"
            elif metric.value <= metric.benchmark:
                return "良好"
            elif metric.value <= metric.benchmark * 1.2:
                return "一般"
            else:
                return "较差"
    
    def _calculate_metric_score(self, metric: PerformanceMetric) -> float:
        """计算指标得分 (0-100)"""
        if metric.benchmark is None:
            return 50.0
        
        if metric.is_better_higher:
            ratio = metric.value / metric.benchmark if metric.benchmark != 0 else 1
            score = min(100, max(0, ratio * 50))
        else:
            ratio = metric.benchmark / metric.value if metric.value != 0 else 1
            score = min(100, max(0, ratio * 50))
        
        return round(score, 1)
    
    def _generate_warnings(self, metrics: Dict[str, PerformanceMetric]) -> List[str]:
        """生成警告信息"""
        warnings = []
        
        # 检查关键风险指标
        if 'max_drawdown' in metrics and metrics['max_drawdown'].value > 0.2:
            warnings.append("最大回撤过大，建议加强风险控制")
        
        if 'win_rate' in metrics and metrics['win_rate'].value < 0.4:
            warnings.append("胜率偏低，建议优化策略逻辑")
        
        if 'signal_frequency' in metrics and metrics['signal_frequency'].value > 10:
            warnings.append("信号频率过高，可能存在过度交易")
        
        if 'volatility' in metrics and metrics['volatility'].value > 0.5:
            warnings.append("波动率过高，风险较大")
        
        return warnings
    
    def _generate_recommendations(self, metrics: Dict[str, PerformanceMetric]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于指标表现给出建议
        if 'sharpe_ratio' in metrics and metrics['sharpe_ratio'].value < 1.0:
            recommendations.append("夏普比率偏低，建议优化风险收益比")
        
        if 'signal_balance' in metrics and metrics['signal_balance'].value < 0.6:
            recommendations.append("买卖信号不均衡，建议调整策略参数")
        
        if 'strong_signal_ratio' in metrics and metrics['strong_signal_ratio'].value < 0.2:
            recommendations.append("强信号比例偏低，建议提高信号质量")
        
        return recommendations
