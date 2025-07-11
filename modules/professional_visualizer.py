"""
专业回测可视化模块
创建机构级别的图表和报告
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
sns.set_palette("husl")

class ProfessionalVisualizer:
    """专业可视化器"""
    
    def __init__(self, figsize=(20, 24)):
        self.figsize = figsize
        self.colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72', 
            'success': '#F18F01',
            'danger': '#C73E1D',
            'warning': '#F4A261',
            'info': '#264653',
            'light': '#F8F9FA',
            'dark': '#212529'
        }
    
    def create_comprehensive_report(self, analysis_results: Dict, 
                                  price_data: pd.DataFrame,
                                  trades: pd.DataFrame = None,
                                  save_path: str = None) -> plt.Figure:
        """
        创建综合回测报告
        
        Args:
            analysis_results: 分析结果字典
            price_data: 价格数据
            trades: 交易记录
            save_path: 保存路径
        """
        # 创建大图表
        fig = plt.figure(figsize=self.figsize)
        
        # 创建网格布局 (6行3列)
        gs = fig.add_gridspec(6, 3, hspace=0.3, wspace=0.3)
        
        # 1. 权益曲线和回撤 (第一行，跨3列)
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_equity_and_drawdown(ax1, analysis_results)
        
        # 2. 价格图表和交易信号 (第二行，跨3列)
        ax2 = fig.add_subplot(gs[1, :])
        self._plot_price_and_signals(ax2, price_data, trades)
        
        # 3. 收益分布 (第三行左)
        ax3 = fig.add_subplot(gs[2, 0])
        self._plot_returns_distribution(ax3, analysis_results)
        
        # 4. 月度收益热力图 (第三行中)
        ax4 = fig.add_subplot(gs[2, 1])
        self._plot_monthly_returns_heatmap(ax4, analysis_results)
        
        # 5. 风险指标雷达图 (第三行右)
        ax5 = fig.add_subplot(gs[2, 2])
        self._plot_risk_radar(ax5, analysis_results)
        
        # 6. 滚动夏普比率 (第四行左)
        ax6 = fig.add_subplot(gs[3, 0])
        self._plot_rolling_sharpe(ax6, analysis_results)
        
        # 7. 交易分析 (第四行中)
        ax7 = fig.add_subplot(gs[3, 1])
        self._plot_trade_analysis(ax7, analysis_results)
        
        # 8. 回撤分析 (第四行右)
        ax8 = fig.add_subplot(gs[3, 2])
        self._plot_drawdown_analysis(ax8, analysis_results)
        
        # 9. 周期性表现 (第五行左)
        ax9 = fig.add_subplot(gs[4, 0])
        self._plot_periodic_performance(ax9, analysis_results)
        
        # 10. VaR分析 (第五行中)
        ax10 = fig.add_subplot(gs[4, 1])
        self._plot_var_analysis(ax10, analysis_results)
        
        # 11. 关键指标仪表盘 (第五行右)
        ax11 = fig.add_subplot(gs[4, 2])
        self._plot_key_metrics_dashboard(ax11, analysis_results)
        
        # 12. 文字摘要 (第六行，跨3列)
        ax12 = fig.add_subplot(gs[5, :])
        self._plot_text_summary(ax12, analysis_results)
        
        # 设置总标题
        fig.suptitle('📊 专业量化交易回测分析报告', 
                    fontsize=24, fontweight='bold', y=0.98)
        
        # 保存图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📊 专业回测报告已保存到: {save_path}")
        
        return fig
    
    def _plot_equity_and_drawdown(self, ax, results):
        """绘制权益曲线和回撤"""
        equity = results['cumulative_returns'] + 1
        drawdown = results['drawdown_series']
        
        # 权益曲线
        ax2 = ax.twinx()
        
        line1 = ax.plot(equity.index, equity.values, 
                       color=self.colors['primary'], linewidth=2, 
                       label='权益曲线', alpha=0.8)
        
        # 回撤填充
        ax2.fill_between(drawdown.index, drawdown.values, 0, 
                        color=self.colors['danger'], alpha=0.3, 
                        label='回撤')
        ax2.plot(drawdown.index, drawdown.values, 
                color=self.colors['danger'], linewidth=1)
        
        ax.set_title('📈 权益曲线与回撤分析', fontsize=14, fontweight='bold')
        ax.set_ylabel('累计收益率', color=self.colors['primary'])
        ax2.set_ylabel('回撤', color=self.colors['danger'])
        
        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.tick_params(axis='x', rotation=45)
        
        # 添加网格
        ax.grid(True, alpha=0.3)
        
        # 图例
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    def _plot_price_and_signals(self, ax, price_data, trades):
        """绘制价格和交易信号"""
        # 价格线
        ax.plot(price_data.index, price_data['close'], 
               color=self.colors['info'], linewidth=1.5, 
               label='价格', alpha=0.8)
        
        # 移动平均线 (如果有)
        if 'fast_ma' in price_data.columns:
            ax.plot(price_data.index, price_data['fast_ma'], 
                   color=self.colors['warning'], linewidth=1, 
                   label='快速MA', alpha=0.7)
        
        if 'slow_ma' in price_data.columns:
            ax.plot(price_data.index, price_data['slow_ma'], 
                   color=self.colors['secondary'], linewidth=1, 
                   label='慢速MA', alpha=0.7)
        
        # 交易信号
        if trades is not None and not trades.empty:
            buy_trades = trades[trades['side'] == 'buy'] if 'side' in trades.columns else pd.DataFrame()
            sell_trades = trades[trades['side'] == 'sell'] if 'side' in trades.columns else pd.DataFrame()
            
            if not buy_trades.empty:
                ax.scatter(buy_trades.index, buy_trades['price'], 
                          color=self.colors['success'], marker='^', 
                          s=100, label='买入', zorder=5)
            
            if not sell_trades.empty:
                ax.scatter(sell_trades.index, sell_trades['price'], 
                          color=self.colors['danger'], marker='v', 
                          s=100, label='卖出', zorder=5)
        
        ax.set_title('💹 价格走势与交易信号', fontsize=14, fontweight='bold')
        ax.set_ylabel('价格')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_returns_distribution(self, ax, results):
        """绘制收益分布"""
        returns = results['daily_returns']
        
        # 直方图
        ax.hist(returns, bins=50, alpha=0.7, color=self.colors['primary'], 
               density=True, edgecolor='white')
        
        # 正态分布拟合
        mu, sigma = returns.mean(), returns.std()
        x = np.linspace(returns.min(), returns.max(), 100)
        normal_dist = (1/(sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        ax.plot(x, normal_dist, color=self.colors['danger'], linewidth=2, 
               label='正态分布拟合')
        
        # 添加统计信息
        ax.axvline(mu, color=self.colors['warning'], linestyle='--', 
                  label=f'均值: {mu:.4f}')
        ax.axvline(results['var_95'], color=self.colors['danger'], 
                  linestyle='--', label=f'95% VaR: {results["var_95"]:.4f}')
        
        ax.set_title('📊 日收益率分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('日收益率')
        ax.set_ylabel('密度')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def _plot_monthly_returns_heatmap(self, ax, results):
        """绘制月度收益热力图"""
        monthly_returns = results['monthly_returns']
        
        if len(monthly_returns) > 0:
            # 创建月度收益矩阵
            monthly_data = monthly_returns.to_frame('returns')
            monthly_data['year'] = monthly_data.index.year
            monthly_data['month'] = monthly_data.index.month
            
            pivot_table = monthly_data.pivot_table(
                values='returns', index='year', columns='month', 
                aggfunc='mean'
            )
            
            # 热力图
            sns.heatmap(pivot_table, annot=True, fmt='.2%', 
                       cmap='RdYlGn', center=0, ax=ax,
                       cbar_kws={'label': '月收益率'})
            
            ax.set_title('🗓️ 月度收益热力图', fontsize=12, fontweight='bold')
            ax.set_xlabel('月份')
            ax.set_ylabel('年份')
        else:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('🗓️ 月度收益热力图', fontsize=12, fontweight='bold')
    
    def _plot_risk_radar(self, ax, results):
        """绘制风险指标雷达图"""
        # 风险指标 (标准化到0-1)
        metrics = {
            '夏普比率': min(max(results['sharpe_ratio'] / 3, 0), 1),
            '索提诺比率': min(max(results['sortino_ratio'] / 3, 0), 1),
            '卡尔马比率': min(max(results['calmar_ratio'] / 5, 0), 1),
            '胜率': results['win_rate'],
            '盈亏比': min(max(results['profit_factor'] / 5, 0), 1),
            '稳定性': max(1 - results['annualized_volatility'], 0)
        }
        
        # 雷达图数据
        categories = list(metrics.keys())
        values = list(metrics.values())
        
        # 角度
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]  # 闭合
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, values, 'o-', linewidth=2, 
               color=self.colors['primary'], alpha=0.8)
        ax.fill(angles, values, alpha=0.25, color=self.colors['primary'])
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8)
        ax.grid(True, alpha=0.3)
        
        ax.set_title('🎯 风险指标雷达图', fontsize=12, fontweight='bold')
    
    def _plot_rolling_sharpe(self, ax, results):
        """绘制滚动夏普比率"""
        returns = results['daily_returns']
        
        # 计算30天滚动夏普比率
        rolling_sharpe = returns.rolling(30).mean() / returns.rolling(30).std() * np.sqrt(252)
        
        ax.plot(rolling_sharpe.index, rolling_sharpe.values, 
               color=self.colors['primary'], linewidth=1.5)
        ax.axhline(y=1, color=self.colors['success'], linestyle='--', 
                  alpha=0.7, label='优秀线 (1.0)')
        ax.axhline(y=0, color=self.colors['danger'], linestyle='--', 
                  alpha=0.7, label='基准线 (0.0)')
        
        ax.set_title('📈 滚动夏普比率 (30天)', fontsize=12, fontweight='bold')
        ax.set_ylabel('夏普比率')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_trade_analysis(self, ax, results):
        """绘制交易分析"""
        # 交易统计数据
        trade_stats = {
            '总交易': results['total_trades'],
            '盈利交易': results['winning_trades'],
            '亏损交易': results['losing_trades']
        }
        
        # 饼图
        sizes = [results['winning_trades'], results['losing_trades']]
        labels = ['盈利交易', '亏损交易']
        colors = [self.colors['success'], self.colors['danger']]
        
        if sum(sizes) > 0:
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                            autopct='%1.1f%%', startangle=90)
            
            # 添加统计信息
            stats_text = f"""
总交易: {results['total_trades']}
胜率: {results['win_rate']:.1%}
盈亏比: {results['profit_factor']:.2f}
期望: {results['expectancy']:.4f}
            """.strip()
            
            ax.text(1.3, 0.5, stats_text, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='center',
                   bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        else:
            ax.text(0.5, 0.5, '无交易数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
        
        ax.set_title('💼 交易分析', fontsize=12, fontweight='bold')
    
    def _plot_drawdown_analysis(self, ax, results):
        """绘制回撤分析"""
        drawdown = results['drawdown_series']
        
        # 回撤曲线
        ax.fill_between(drawdown.index, drawdown.values, 0, 
                       color=self.colors['danger'], alpha=0.6)
        ax.plot(drawdown.index, drawdown.values, 
               color=self.colors['danger'], linewidth=1.5)
        
        # 标记最大回撤点
        max_dd_date = results['max_drawdown_date']
        max_dd_value = results['max_drawdown']
        
        ax.scatter([max_dd_date], [-max_dd_value], 
                  color='red', s=100, zorder=5, 
                  label=f'最大回撤: {max_dd_value:.2%}')
        
        ax.set_title('📉 回撤分析', fontsize=12, fontweight='bold')
        ax.set_ylabel('回撤')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_periodic_performance(self, ax, results):
        """绘制周期性表现"""
        weekly_perf = results.get('weekly_performance', {})
        
        if weekly_perf:
            days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            returns = [weekly_perf.get(i, {}).get('avg_return', 0) for i in range(7)]
            
            colors = [self.colors['success'] if r > 0 else self.colors['danger'] for r in returns]
            
            bars = ax.bar(days, returns, color=colors, alpha=0.7)
            
            # 添加数值标签
            for bar, ret in zip(bars, returns):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{ret:.3f}', ha='center', va='bottom' if height > 0 else 'top',
                       fontsize=8)
            
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            ax.set_title('📅 周内表现', fontsize=12, fontweight='bold')
            ax.set_ylabel('平均日收益率')
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('📅 周内表现', fontsize=12, fontweight='bold')
    
    def _plot_var_analysis(self, ax, results):
        """绘制VaR分析"""
        returns = results['daily_returns']
        
        # VaR值
        var_95 = results['var_95']
        var_99 = results['var_99']
        cvar_95 = results['cvar_95']
        
        # 直方图
        ax.hist(returns, bins=30, alpha=0.7, color=self.colors['info'], 
               density=True, edgecolor='white')
        
        # VaR线
        ax.axvline(var_95, color=self.colors['warning'], linestyle='--', 
                  linewidth=2, label=f'95% VaR: {var_95:.3f}')
        ax.axvline(var_99, color=self.colors['danger'], linestyle='--', 
                  linewidth=2, label=f'99% VaR: {var_99:.3f}')
        ax.axvline(cvar_95, color='red', linestyle='-', 
                  linewidth=2, label=f'95% CVaR: {cvar_95:.3f}')
        
        ax.set_title('⚠️ 风险价值分析', fontsize=12, fontweight='bold')
        ax.set_xlabel('日收益率')
        ax.set_ylabel('密度')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    def _plot_key_metrics_dashboard(self, ax, results):
        """绘制关键指标仪表盘"""
        # 关键指标
        metrics = {
            '总收益率': f"{results['total_return']:.2%}",
            '年化收益': f"{results['annualized_return']:.2%}",
            '最大回撤': f"{results['max_drawdown']:.2%}",
            '夏普比率': f"{results['sharpe_ratio']:.3f}",
            '胜率': f"{results['win_rate']:.1%}",
            '盈亏比': f"{results['profit_factor']:.2f}"
        }
        
        # 创建表格样式的显示
        y_positions = np.linspace(0.9, 0.1, len(metrics))
        
        for i, (key, value) in enumerate(metrics.items()):
            # 指标名称
            ax.text(0.1, y_positions[i], key, fontsize=12, fontweight='bold',
                   transform=ax.transAxes, ha='left')
            
            # 指标值
            color = self.colors['success'] if any(x in key for x in ['收益', '夏普', '胜率', '盈亏']) else self.colors['info']
            if '回撤' in key:
                color = self.colors['danger']
            
            ax.text(0.7, y_positions[i], value, fontsize=14, fontweight='bold',
                   transform=ax.transAxes, ha='right', color=color)
            
            # 分隔线
            if i < len(metrics) - 1:
                ax.axhline(y=y_positions[i] - 0.06, xmin=0.1, xmax=0.9, 
                          color='gray', alpha=0.3)
        
        ax.set_title('📊 关键指标仪表盘', fontsize=12, fontweight='bold')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
    
    def _plot_text_summary(self, ax, results):
        """绘制文字摘要"""
        # 生成摘要文本
        summary_text = f"""
📊 回测摘要报告

🎯 收益表现: 策略在回测期间实现了 {results['total_return']:.2%} 的总收益率，年化收益率为 {results['annualized_return']:.2%}。
   最佳单日收益为 {results['best_day']:.2%}，最差单日亏损为 {results['worst_day']:.2%}。

⚠️ 风险控制: 策略的最大回撤为 {results['max_drawdown']:.2%}，年化波动率为 {results['annualized_volatility']:.2%}。
   95%置信度下的日VaR为 {results['var_95']:.3f}，显示了良好的风险控制能力。

📈 风险调整收益: 夏普比率为 {results['sharpe_ratio']:.3f}，索提诺比率为 {results['sortino_ratio']:.3f}，
   卡尔马比率为 {results['calmar_ratio']:.3f}，表明策略具有较好的风险调整后收益。

💼 交易效率: 总共执行了 {results['total_trades']} 笔交易，胜率为 {results['win_rate']:.1%}，
   盈亏比为 {results['profit_factor']:.2f}，期望收益为 {results['expectancy']:.4f}。

🔍 综合评价: {'该策略表现优秀，建议进一步优化参数或增加仓位。' if results['sharpe_ratio'] > 1 else '该策略表现一般，建议优化策略逻辑或风险管理。' if results['sharpe_ratio'] > 0 else '该策略表现较差，需要重新设计策略逻辑。'}
        """.strip()
        
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, 
               fontsize=11, verticalalignment='top', 
               bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.1))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
