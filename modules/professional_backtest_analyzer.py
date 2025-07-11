"""
专业回测分析器
提供机构级别的回测分析指标和可视化
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class ProfessionalBacktestAnalyzer:
    """专业回测分析器"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 无风险利率 2%
        
    def analyze_backtest_results(self, equity_curve: pd.Series, 
                               trades: pd.DataFrame,
                               benchmark: pd.Series = None) -> Dict:
        """
        全面分析回测结果
        
        Args:
            equity_curve: 权益曲线 (时间序列)
            trades: 交易记录 DataFrame
            benchmark: 基准收益率 (可选)
            
        Returns:
            完整的分析结果字典
        """
        results = {}
        
        # 基础收益指标
        results.update(self._calculate_return_metrics(equity_curve))
        
        # 风险指标
        results.update(self._calculate_risk_metrics(equity_curve))
        
        # 交易分析
        results.update(self._analyze_trades(trades))
        
        # 回撤分析
        results.update(self._analyze_drawdowns(equity_curve))
        
        # 时间分析
        results.update(self._analyze_time_periods(equity_curve))
        
        # 基准比较 (如果提供)
        if benchmark is not None:
            results.update(self._compare_with_benchmark(equity_curve, benchmark))
        
        # 风险调整收益
        results.update(self._calculate_risk_adjusted_returns(equity_curve))
        
        return results
    
    def _calculate_return_metrics(self, equity_curve: pd.Series) -> Dict:
        """计算收益指标"""
        returns = equity_curve.pct_change().dropna()
        
        # 基础收益指标
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        
        # 年化收益率
        trading_days = len(equity_curve)
        years = trading_days / 252  # 假设252个交易日/年
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # 累计收益率
        cumulative_returns = (equity_curve / equity_curve.iloc[0]) - 1
        
        # 月度收益率
        monthly_returns = equity_curve.resample('M').last().pct_change().dropna()
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'cumulative_returns': cumulative_returns,
            'daily_returns': returns,
            'monthly_returns': monthly_returns,
            'avg_daily_return': returns.mean(),
            'avg_monthly_return': monthly_returns.mean(),
            'positive_days_ratio': (returns > 0).sum() / len(returns),
            'best_day': returns.max(),
            'worst_day': returns.min(),
            'best_month': monthly_returns.max(),
            'worst_month': monthly_returns.min()
        }
    
    def _calculate_risk_metrics(self, equity_curve: pd.Series) -> Dict:
        """计算风险指标"""
        returns = equity_curve.pct_change().dropna()
        
        # 波动率
        daily_volatility = returns.std()
        annualized_volatility = daily_volatility * np.sqrt(252)
        
        # 下行风险
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        
        # VaR (风险价值)
        var_95 = returns.quantile(0.05)  # 95% VaR
        var_99 = returns.quantile(0.01)  # 99% VaR
        
        # CVaR (条件风险价值)
        cvar_95 = returns[returns <= var_95].mean()
        cvar_99 = returns[returns <= var_99].mean()
        
        # 偏度和峰度
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        return {
            'daily_volatility': daily_volatility,
            'annualized_volatility': annualized_volatility,
            'downside_deviation': downside_deviation,
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'volatility_of_volatility': returns.rolling(30).std().std()
        }
    
    def _analyze_trades(self, trades: pd.DataFrame) -> Dict:
        """分析交易记录"""
        if trades.empty:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'avg_trade_duration': 0
            }
        
        # 基础交易统计
        total_trades = len(trades)
        winning_trades = len(trades[trades['pnl'] > 0])
        losing_trades = len(trades[trades['pnl'] < 0])
        
        # 胜率
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 平均盈亏
        wins = trades[trades['pnl'] > 0]['pnl']
        losses = trades[trades['pnl'] < 0]['pnl']
        
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        
        # 盈亏比
        profit_factor = abs(wins.sum() / losses.sum()) if losses.sum() != 0 else float('inf')
        
        # 最大连续盈亏
        trades['win'] = trades['pnl'] > 0
        max_consecutive_wins = self._max_consecutive(trades['win'], True)
        max_consecutive_losses = self._max_consecutive(trades['win'], False)
        
        # 交易持续时间
        if 'entry_time' in trades.columns and 'exit_time' in trades.columns:
            trades['duration'] = (trades['exit_time'] - trades['entry_time']).dt.total_seconds() / 3600  # 小时
            avg_trade_duration = trades['duration'].mean()
        else:
            avg_trade_duration = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'avg_trade_duration': avg_trade_duration,
            'largest_win': trades['pnl'].max(),
            'largest_loss': trades['pnl'].min(),
            'expectancy': (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        }
    
    def _analyze_drawdowns(self, equity_curve: pd.Series) -> Dict:
        """分析回撤"""
        # 计算回撤
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        
        # 最大回撤
        max_drawdown = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # 回撤持续时间
        in_drawdown = drawdown < 0
        drawdown_periods = []
        
        start = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start is None:
                start = i
            elif not is_dd and start is not None:
                drawdown_periods.append(i - start)
                start = None
        
        if start is not None:  # 如果最后还在回撤中
            drawdown_periods.append(len(in_drawdown) - start)
        
        avg_drawdown_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # 回撤恢复时间
        recovery_times = []
        for i in range(len(equity_curve)):
            if drawdown.iloc[i] == 0 and i > 0:  # 新高点
                # 找到之前的回撤开始点
                for j in range(i-1, -1, -1):
                    if drawdown.iloc[j] == 0:
                        recovery_times.append(i - j)
                        break
        
        avg_recovery_time = np.mean(recovery_times) if recovery_times else 0
        
        return {
            'max_drawdown': abs(max_drawdown),
            'max_drawdown_date': max_dd_date,
            'avg_drawdown_duration': avg_drawdown_duration,
            'max_drawdown_duration': max_drawdown_duration,
            'avg_recovery_time': avg_recovery_time,
            'drawdown_series': drawdown,
            'num_drawdown_periods': len(drawdown_periods),
            'time_in_drawdown': (drawdown < 0).sum() / len(drawdown)
        }
    
    def _analyze_time_periods(self, equity_curve: pd.Series) -> Dict:
        """分析不同时间周期的表现"""
        returns = equity_curve.pct_change().dropna()
        
        # 按月份分析
        monthly_performance = {}
        for month in range(1, 13):
            month_returns = returns[returns.index.month == month]
            if len(month_returns) > 0:
                monthly_performance[month] = {
                    'avg_return': month_returns.mean(),
                    'volatility': month_returns.std(),
                    'win_rate': (month_returns > 0).sum() / len(month_returns)
                }
        
        # 按星期分析
        weekly_performance = {}
        for day in range(7):
            day_returns = returns[returns.index.dayofweek == day]
            if len(day_returns) > 0:
                weekly_performance[day] = {
                    'avg_return': day_returns.mean(),
                    'volatility': day_returns.std(),
                    'win_rate': (day_returns > 0).sum() / len(day_returns)
                }
        
        return {
            'monthly_performance': monthly_performance,
            'weekly_performance': weekly_performance
        }
    
    def _compare_with_benchmark(self, equity_curve: pd.Series, benchmark: pd.Series) -> Dict:
        """与基准比较"""
        strategy_returns = equity_curve.pct_change().dropna()
        benchmark_returns = benchmark.pct_change().dropna()
        
        # 对齐时间序列
        common_dates = strategy_returns.index.intersection(benchmark_returns.index)
        strategy_aligned = strategy_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # 相关性
        correlation = strategy_aligned.corr(benchmark_aligned)
        
        # Beta
        covariance = np.cov(strategy_aligned, benchmark_aligned)[0][1]
        benchmark_variance = benchmark_aligned.var()
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0
        
        # Alpha
        strategy_annual_return = (1 + strategy_aligned.mean()) ** 252 - 1
        benchmark_annual_return = (1 + benchmark_aligned.mean()) ** 252 - 1
        alpha = strategy_annual_return - (self.risk_free_rate + beta * (benchmark_annual_return - self.risk_free_rate))
        
        # 信息比率
        excess_returns = strategy_aligned - benchmark_aligned
        information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() != 0 else 0
        
        return {
            'correlation_with_benchmark': correlation,
            'beta': beta,
            'alpha': alpha,
            'information_ratio': information_ratio,
            'excess_returns': excess_returns
        }
    
    def _calculate_risk_adjusted_returns(self, equity_curve: pd.Series) -> Dict:
        """计算风险调整收益指标"""
        returns = equity_curve.pct_change().dropna()
        
        # 夏普比率
        excess_returns = returns.mean() - (self.risk_free_rate / 252)
        sharpe_ratio = excess_returns / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
        
        # 索提诺比率 (Sortino Ratio)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std()
        sortino_ratio = excess_returns / downside_std * np.sqrt(252) if downside_std != 0 else 0
        
        # 卡尔马比率 (Calmar Ratio)
        annual_return = (1 + returns.mean()) ** 252 - 1
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        calmar_ratio = annual_return / max_drawdown if max_drawdown != 0 else 0
        
        # Omega比率
        threshold = 0  # 阈值收益率
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        omega_ratio = gains / losses if losses != 0 else float('inf')
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'omega_ratio': omega_ratio
        }
    
    def _max_consecutive(self, series: pd.Series, value: bool) -> int:
        """计算最大连续出现次数"""
        max_count = 0
        current_count = 0
        
        for val in series:
            if val == value:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    def generate_performance_summary(self, analysis_results: Dict) -> str:
        """生成性能摘要报告"""
        summary = []
        summary.append("=" * 60)
        summary.append("📊 专业回测分析报告")
        summary.append("=" * 60)
        
        # 收益指标
        summary.append("\n🎯 收益指标:")
        summary.append(f"  总收益率: {analysis_results['total_return']:.2%}")
        summary.append(f"  年化收益率: {analysis_results['annualized_return']:.2%}")
        summary.append(f"  最佳单日: {analysis_results['best_day']:.2%}")
        summary.append(f"  最差单日: {analysis_results['worst_day']:.2%}")
        
        # 风险指标
        summary.append("\n⚠️ 风险指标:")
        summary.append(f"  年化波动率: {analysis_results['annualized_volatility']:.2%}")
        summary.append(f"  最大回撤: {analysis_results['max_drawdown']:.2%}")
        summary.append(f"  95% VaR: {analysis_results['var_95']:.2%}")
        summary.append(f"  下行偏差: {analysis_results['downside_deviation']:.2%}")
        
        # 风险调整收益
        summary.append("\n📈 风险调整收益:")
        summary.append(f"  夏普比率: {analysis_results['sharpe_ratio']:.4f}")
        summary.append(f"  索提诺比率: {analysis_results['sortino_ratio']:.4f}")
        summary.append(f"  卡尔马比率: {analysis_results['calmar_ratio']:.4f}")
        
        # 交易分析
        summary.append("\n💼 交易分析:")
        summary.append(f"  总交易次数: {analysis_results['total_trades']}")
        summary.append(f"  胜率: {analysis_results['win_rate']:.2%}")
        summary.append(f"  盈亏比: {analysis_results['profit_factor']:.2f}")
        summary.append(f"  期望收益: {analysis_results['expectancy']:.4f}")
        
        summary.append("=" * 60)
        
        return "\n".join(summary)
