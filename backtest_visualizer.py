"""
回测可视化分析器
生成详细的回测图表和报告
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

class BacktestVisualizer:
    """回测可视化分析器"""
    
    def __init__(self, figsize=(15, 12)):
        self.figsize = figsize
        self.colors = {
            'buy': '#2E8B57',      # 海绿色
            'sell': '#DC143C',     # 深红色
            'price': '#1f77b4',    # 蓝色
            'ma_fast': '#ff7f0e',  # 橙色
            'ma_slow': '#2ca02c',  # 绿色
            'bb_upper': '#d62728', # 红色
            'bb_lower': '#d62728', # 红色
            'bb_middle': '#9467bd', # 紫色
            'equity': '#2E8B57',   # 海绿色
            'drawdown': '#DC143C', # 深红色
        }
    
    def create_comprehensive_report(self, backtest_result: Dict, 
                                  save_path: str = None) -> None:
        """
        创建综合回测报告
        
        Args:
            backtest_result: 回测结果字典
            save_path: 保存路径
        """
        # 提取数据
        data = backtest_result['signals']
        trades = backtest_result.get('trades', [])
        equity_curve = backtest_result.get('equity_curve', pd.DataFrame())
        strategy_name = backtest_result.get('strategy_name', 'Unknown')
        symbol = backtest_result.get('symbol', 'Unknown')
        
        # 创建图表
        fig = plt.figure(figsize=(20, 16))
        
        # 1. 价格图表和交易信号 (占2行)
        ax1 = plt.subplot(4, 2, (1, 2))
        self._plot_price_and_signals(ax1, data, trades, strategy_name, symbol)
        
        # 2. 权益曲线 (占1行)
        ax2 = plt.subplot(4, 2, (3, 4))
        self._plot_equity_curve(ax2, equity_curve, backtest_result)
        
        # 3. 技术指标
        ax3 = plt.subplot(4, 2, 5)
        self._plot_technical_indicators(ax3, data)
        
        # 4. 成交量
        ax4 = plt.subplot(4, 2, 6)
        self._plot_volume(ax4, data, trades)
        
        # 5. 回撤分析
        ax5 = plt.subplot(4, 2, 7)
        self._plot_drawdown_analysis(ax5, equity_curve)
        
        # 6. 交易统计
        ax6 = plt.subplot(4, 2, 8)
        self._plot_trade_statistics(ax6, trades, backtest_result)
        
        plt.tight_layout(pad=3.0)
        
        # 添加总标题
        fig.suptitle(f'{strategy_name} - {symbol} 回测分析报告', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📊 回测报告已保存到: {save_path}")
        
        plt.show()
    
    def _plot_price_and_signals(self, ax, data: pd.DataFrame, trades: List, 
                               strategy_name: str, symbol: str):
        """绘制价格图表和交易信号"""
        # 绘制价格线
        ax.plot(data.index, data['close'], label='价格', 
               color=self.colors['price'], linewidth=1.5, alpha=0.8)
        
        # 绘制移动平均线(如果存在)
        if 'fast_ma' in data.columns:
            ax.plot(data.index, data['fast_ma'], label='快速MA', 
                   color=self.colors['ma_fast'], linewidth=1, alpha=0.7)
        if 'slow_ma' in data.columns:
            ax.plot(data.index, data['slow_ma'], label='慢速MA', 
                   color=self.colors['ma_slow'], linewidth=1, alpha=0.7)
        
        # 绘制布林带(如果存在)
        if 'bb_upper' in data.columns:
            ax.plot(data.index, data['bb_upper'], label='布林带上轨', 
                   color=self.colors['bb_upper'], linewidth=1, alpha=0.5, linestyle='--')
            ax.plot(data.index, data['bb_lower'], label='布林带下轨', 
                   color=self.colors['bb_lower'], linewidth=1, alpha=0.5, linestyle='--')
            ax.plot(data.index, data['bb_middle'], label='布林带中轨', 
                   color=self.colors['bb_middle'], linewidth=1, alpha=0.5)
            
            # 填充布林带区域
            ax.fill_between(data.index, data['bb_upper'], data['bb_lower'], 
                           alpha=0.1, color='gray')
        
        # 绘制唐奇安通道(如果存在)
        if 'donchian_upper' in data.columns:
            ax.plot(data.index, data['donchian_upper'], label='唐奇安上轨', 
                   color='red', linewidth=1, alpha=0.5, linestyle=':')
            ax.plot(data.index, data['donchian_lower'], label='唐奇安下轨', 
                   color='red', linewidth=1, alpha=0.5, linestyle=':')
        
        # 标记买卖点
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        
        if not buy_signals.empty:
            ax.scatter(buy_signals.index, buy_signals['close'], 
                      marker='^', s=100, color=self.colors['buy'], 
                      label=f'买入信号 ({len(buy_signals)})', zorder=5, alpha=0.8)
        
        if not sell_signals.empty:
            ax.scatter(sell_signals.index, sell_signals['close'], 
                      marker='v', s=100, color=self.colors['sell'], 
                      label=f'卖出信号 ({len(sell_signals)})', zorder=5, alpha=0.8)
        
        # 标记实际交易点
        if trades:
            buy_trades = [t for t in trades if t.get('type') == 'buy']
            sell_trades = [t for t in trades if t.get('type') == 'sell']
            
            if buy_trades:
                buy_times = [t['timestamp'] for t in buy_trades]
                buy_prices = [t['price'] for t in buy_trades]
                ax.scatter(buy_times, buy_prices, marker='o', s=80, 
                          color=self.colors['buy'], edgecolor='white', 
                          linewidth=2, label=f'实际买入 ({len(buy_trades)})', zorder=6)
            
            if sell_trades:
                sell_times = [t['timestamp'] for t in sell_trades]
                sell_prices = [t['price'] for t in sell_trades]
                ax.scatter(sell_times, sell_prices, marker='o', s=80, 
                          color=self.colors['sell'], edgecolor='white', 
                          linewidth=2, label=f'实际卖出 ({len(sell_trades)})', zorder=6)
        
        ax.set_title(f'{symbol} 价格走势与交易信号', fontsize=14, fontweight='bold')
        ax.set_ylabel('价格', fontsize=12)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴
        if len(data) > 100:
            ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    
    def _plot_equity_curve(self, ax, equity_curve: pd.DataFrame, backtest_result: Dict):
        """绘制权益曲线"""
        if equity_curve.empty:
            ax.text(0.5, 0.5, '无权益曲线数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # 绘制权益曲线
        ax.plot(equity_curve.index, equity_curve['equity'], 
               color=self.colors['equity'], linewidth=2, label='组合价值')
        
        # 添加基准线
        initial_capital = backtest_result.get('initial_capital', 10000)
        ax.axhline(y=initial_capital, color='gray', linestyle='--', 
                  alpha=0.5, label='初始资金')
        
        # 计算并绘制回撤
        peak = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - peak) / peak
        
        # 在副y轴绘制回撤
        ax2 = ax.twinx()
        ax2.fill_between(equity_curve.index, 0, drawdown * 100, 
                        color=self.colors['drawdown'], alpha=0.3, label='回撤%')
        ax2.set_ylabel('回撤 (%)', fontsize=12, color=self.colors['drawdown'])
        ax2.tick_params(axis='y', labelcolor=self.colors['drawdown'])
        
        # 标记最大回撤点
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        if not pd.isna(max_dd_value):
            ax.annotate(f'最大回撤: {max_dd_value:.2%}', 
                       xy=(max_dd_idx, equity_curve.loc[max_dd_idx, 'equity']),
                       xytext=(10, 10), textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color='red'))
        
        # 添加收益率信息
        final_equity = equity_curve['equity'].iloc[-1]
        total_return = (final_equity - initial_capital) / initial_capital
        ax.text(0.02, 0.98, f'总收益率: {total_return:.2%}', 
               transform=ax.transAxes, fontsize=12, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7),
               verticalalignment='top')
        
        ax.set_title('组合权益曲线与回撤分析', fontsize=14, fontweight='bold')
        ax.set_ylabel('组合价值', fontsize=12)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _plot_technical_indicators(self, ax, data: pd.DataFrame):
        """绘制技术指标"""
        # 优先绘制RSI
        if 'rsi' in data.columns:
            ax.plot(data.index, data['rsi'], label='RSI', color='purple', linewidth=1.5)
            ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买线')
            ax.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖线')
            ax.fill_between(data.index, 30, 70, alpha=0.1, color='gray')
            ax.set_ylim(0, 100)
            ax.set_ylabel('RSI', fontsize=12)
        
        # 如果没有RSI，绘制其他指标
        elif 'adx' in data.columns:
            ax.plot(data.index, data['adx'], label='ADX', color='orange', linewidth=1.5)
            if 'plus_di' in data.columns:
                ax.plot(data.index, data['plus_di'], label='+DI', color='green', linewidth=1)
            if 'minus_di' in data.columns:
                ax.plot(data.index, data['minus_di'], label='-DI', color='red', linewidth=1)
            ax.axhline(y=25, color='gray', linestyle='--', alpha=0.5, label='趋势阈值')
            ax.set_ylabel('ADX/DI', fontsize=12)
        
        # 如果都没有，绘制价格变化率
        else:
            returns = data['close'].pct_change() * 100
            ax.plot(data.index, returns, label='价格变化率%', color='blue', linewidth=1)
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
            ax.set_ylabel('变化率 (%)', fontsize=12)
        
        ax.set_title('技术指标', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _plot_volume(self, ax, data: pd.DataFrame, trades: List):
        """绘制成交量"""
        if 'volume' not in data.columns:
            ax.text(0.5, 0.5, '无成交量数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # 绘制成交量柱状图
        colors = ['red' if close < open else 'green' 
                 for close, open in zip(data['close'], data['open'])]
        ax.bar(data.index, data['volume'], color=colors, alpha=0.6, width=0.8)
        
        # 绘制成交量移动平均
        if len(data) > 20:
            volume_ma = data['volume'].rolling(window=20).mean()
            ax.plot(data.index, volume_ma, color='blue', linewidth=1, 
                   label='成交量MA(20)', alpha=0.8)
        
        # 标记交易时的成交量
        if trades:
            trade_times = [t['timestamp'] for t in trades if 'timestamp' in t]
            if trade_times:
                trade_volumes = []
                for t_time in trade_times:
                    # 找到最接近的时间点
                    closest_idx = data.index.get_indexer([t_time], method='nearest')[0]
                    if closest_idx < len(data):
                        trade_volumes.append(data.iloc[closest_idx]['volume'])
                    else:
                        trade_volumes.append(0)
                
                ax.scatter(trade_times, trade_volumes, color='yellow', 
                          s=50, edgecolor='black', linewidth=1, 
                          label='交易时成交量', zorder=5)
        
        ax.set_title('成交量分析', fontsize=12, fontweight='bold')
        ax.set_ylabel('成交量', fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def _plot_drawdown_analysis(self, ax, equity_curve: pd.DataFrame):
        """绘制回撤分析"""
        if equity_curve.empty:
            ax.text(0.5, 0.5, '无权益数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # 计算回撤
        peak = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - peak) / peak * 100
        
        # 绘制回撤曲线
        ax.fill_between(equity_curve.index, 0, drawdown, 
                       color=self.colors['drawdown'], alpha=0.6, label='回撤')
        ax.plot(equity_curve.index, drawdown, 
               color=self.colors['drawdown'], linewidth=1.5)
        
        # 标记最大回撤
        max_dd_value = drawdown.min()
        max_dd_idx = drawdown.idxmin()
        
        if not pd.isna(max_dd_value):
            ax.annotate(f'最大回撤: {max_dd_value:.2f}%', 
                       xy=(max_dd_idx, max_dd_value),
                       xytext=(10, -10), textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color='red'))
        
        # 添加回撤统计
        avg_drawdown = drawdown[drawdown < 0].mean()
        drawdown_periods = self._calculate_drawdown_periods(drawdown)
        
        stats_text = f'平均回撤: {avg_drawdown:.2f}%\n回撤期数: {len(drawdown_periods)}'
        ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7))
        
        ax.set_title('回撤分析', fontsize=12, fontweight='bold')
        ax.set_ylabel('回撤 (%)', fontsize=12)
        ax.set_ylim(min(drawdown.min() * 1.1, -1), 1)
        ax.grid(True, alpha=0.3)
    
    def _calculate_drawdown_periods(self, drawdown: pd.Series) -> List:
        """计算回撤期间"""
        periods = []
        in_drawdown = False
        start_idx = None
        
        for idx, value in drawdown.items():
            if value < 0 and not in_drawdown:
                in_drawdown = True
                start_idx = idx
            elif value >= 0 and in_drawdown:
                in_drawdown = False
                if start_idx is not None:
                    periods.append((start_idx, idx))
        
        # 如果最后还在回撤中
        if in_drawdown and start_idx is not None:
            periods.append((start_idx, drawdown.index[-1]))
        
        return periods
    
    def _plot_trade_statistics(self, ax, trades: List, backtest_result: Dict):
        """绘制交易统计"""
        if not trades:
            ax.text(0.5, 0.5, '无交易数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # 提取交易盈亏
        pnl_list = []
        for trade in trades:
            if trade.get('type') == 'sell' and 'pnl' in trade:
                pnl_list.append(trade['pnl'])
        
        if not pnl_list:
            ax.text(0.5, 0.5, '无盈亏数据', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            return
        
        # 绘制盈亏分布直方图
        ax.hist(pnl_list, bins=min(20, len(pnl_list)), alpha=0.7, 
               color='skyblue', edgecolor='black')
        
        # 添加统计线
        mean_pnl = np.mean(pnl_list)
        median_pnl = np.median(pnl_list)
        
        ax.axvline(mean_pnl, color='red', linestyle='--', 
                  label=f'平均盈亏: {mean_pnl:.2f}')
        ax.axvline(median_pnl, color='green', linestyle='--', 
                  label=f'中位数: {median_pnl:.2f}')
        ax.axvline(0, color='black', linestyle='-', alpha=0.5)
        
        # 添加统计信息
        winning_trades = len([p for p in pnl_list if p > 0])
        losing_trades = len([p for p in pnl_list if p < 0])
        win_rate = winning_trades / len(pnl_list) if pnl_list else 0
        
        stats_text = f'总交易: {len(pnl_list)}\n盈利: {winning_trades}\n亏损: {losing_trades}\n胜率: {win_rate:.1%}'
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7),
               verticalalignment='top', horizontalalignment='right')
        
        ax.set_title('交易盈亏分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('盈亏金额', fontsize=12)
        ax.set_ylabel('交易次数', fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
    
    def create_strategy_comparison_chart(self, results: Dict[str, Dict], 
                                       save_path: str = None):
        """创建策略对比图表"""
        if not results:
            print("没有结果数据可比较")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 提取数据
        strategies = list(results.keys())
        metrics = {
            'total_return': [],
            'max_drawdown': [],
            'win_rate': [],
            'sharpe_ratio': []
        }
        
        for strategy in strategies:
            result = results[strategy]
            metrics['total_return'].append(result.get('total_return', 0) * 100)
            metrics['max_drawdown'].append(abs(result.get('max_drawdown', 0)) * 100)
            metrics['win_rate'].append(result.get('win_rate', 0) * 100)
            metrics['sharpe_ratio'].append(result.get('sharpe_ratio', 0))
        
        # 1. 收益率对比
        axes[0, 0].bar(strategies, metrics['total_return'], color='lightgreen', alpha=0.7)
        axes[0, 0].set_title('总收益率对比 (%)', fontweight='bold')
        axes[0, 0].set_ylabel('收益率 (%)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 最大回撤对比
        axes[0, 1].bar(strategies, metrics['max_drawdown'], color='lightcoral', alpha=0.7)
        axes[0, 1].set_title('最大回撤对比 (%)', fontweight='bold')
        axes[0, 1].set_ylabel('回撤 (%)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 胜率对比
        axes[1, 0].bar(strategies, metrics['win_rate'], color='lightblue', alpha=0.7)
        axes[1, 0].set_title('胜率对比 (%)', fontweight='bold')
        axes[1, 0].set_ylabel('胜率 (%)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 夏普比率对比
        axes[1, 1].bar(strategies, metrics['sharpe_ratio'], color='lightyellow', alpha=0.7)
        axes[1, 1].set_title('夏普比率对比', fontweight='bold')
        axes[1, 1].set_ylabel('夏普比率')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.suptitle('策略性能对比分析', fontsize=16, fontweight='bold', y=1.02)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 策略对比图表已保存到: {save_path}")
        
        plt.show()

# 使用示例
if __name__ == "__main__":
    # 这里可以添加测试代码
    print("回测可视化分析器已准备就绪")
    print("使用方法:")
    print("visualizer = BacktestVisualizer()")
    print("visualizer.create_comprehensive_report(backtest_result, 'report.png')")
