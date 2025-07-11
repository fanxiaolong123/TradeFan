#!/usr/bin/env python3
"""
专业回测演示
展示专业级别的回测分析和可视化
"""

import sys
import os
sys.path.append('.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from modules.professional_backtest_analyzer import ProfessionalBacktestAnalyzer
from modules.real_data_source import RealDataSource
from strategies.trend_ma_breakout import TrendMABreakoutStrategy

def create_sample_backtest_data():
    """创建示例回测数据"""
    print("📊 创建示例回测数据...")
    
    # 获取真实价格数据
    data_source = RealDataSource()
    price_data = data_source.get_data(
        symbol='BTCUSDT',
        timeframe='1d',
        start_date='2024-01-01',
        end_date='2024-03-31',
        source='binance'
    )
    
    # 转换格式
    df = price_data.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    
    # 创建策略
    strategy = TrendMABreakoutStrategy(fast_ma=10, slow_ma=30)
    df_with_indicators = strategy.calculate_indicators(df)
    
    # 模拟一些交易信号和权益曲线
    np.random.seed(42)
    initial_capital = 100000
    
    # 创建更有趣的权益曲线
    returns = np.random.normal(0.001, 0.02, len(df))  # 日收益率
    returns[20:30] = np.random.normal(0.005, 0.015, 10)  # 好的时期
    returns[50:60] = np.random.normal(-0.003, 0.025, 10)  # 坏的时期
    
    equity_curve = pd.Series(initial_capital, index=df.index)
    for i in range(1, len(equity_curve)):
        equity_curve.iloc[i] = equity_curve.iloc[i-1] * (1 + returns[i])
    
    # 创建交易记录
    trade_dates = np.random.choice(df.index, size=15, replace=False)
    trade_dates = sorted(trade_dates)
    
    trades_data = []
    for i, date in enumerate(trade_dates):
        pnl = np.random.normal(500, 2000)  # 随机盈亏
        trades_data.append({
            'entry_time': date,
            'exit_time': date + pd.Timedelta(days=np.random.randint(1, 10)),
            'entry_price': df.loc[date, 'close'],
            'exit_price': df.loc[date, 'close'] * (1 + np.random.normal(0, 0.05)),
            'pnl': pnl,
            'side': 'buy' if i % 2 == 0 else 'sell'
        })
    
    trades_df = pd.DataFrame(trades_data)
    
    print(f"✅ 示例数据创建完成")
    print(f"   价格数据: {len(df)} 条")
    print(f"   权益曲线: {len(equity_curve)} 个点")
    print(f"   交易记录: {len(trades_df)} 笔")
    
    return df_with_indicators, equity_curve, trades_df

def demo_professional_analysis():
    """演示专业分析功能"""
    print("🚀 专业回测分析演示")
    print("=" * 60)
    
    # 创建示例数据
    price_data, equity_curve, trades = create_sample_backtest_data()
    
    # 创建专业分析器
    analyzer = ProfessionalBacktestAnalyzer()
    
    print(f"\n🔍 执行专业分析...")
    
    # 执行分析
    results = analyzer.analyze_backtest_results(
        equity_curve=equity_curve,
        trades=trades
    )
    
    print(f"✅ 分析完成，共计算 {len(results)} 个指标")
    
    # 生成摘要报告
    summary = analyzer.generate_performance_summary(results)
    print(f"\n{summary}")
    
    # 详细指标展示
    print(f"\n📊 详细分析指标:")
    print(f"=" * 40)
    
    print(f"💰 收益指标:")
    print(f"   总收益率: {results['total_return']:.2%}")
    print(f"   年化收益率: {results['annualized_return']:.2%}")
    print(f"   最佳单日: {results['best_day']:.2%}")
    print(f"   最差单日: {results['worst_day']:.2%}")
    print(f"   正收益天数比例: {results['positive_days_ratio']:.1%}")
    
    print(f"\n⚠️ 风险指标:")
    print(f"   年化波动率: {results['annualized_volatility']:.2%}")
    print(f"   最大回撤: {results['max_drawdown']:.2%}")
    print(f"   下行偏差: {results['downside_deviation']:.2%}")
    print(f"   95% VaR: {results['var_95']:.3f}")
    print(f"   99% VaR: {results['var_99']:.3f}")
    print(f"   偏度: {results['skewness']:.3f}")
    print(f"   峰度: {results['kurtosis']:.3f}")
    
    print(f"\n📈 风险调整收益:")
    print(f"   夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"   索提诺比率: {results['sortino_ratio']:.4f}")
    print(f"   卡尔马比率: {results['calmar_ratio']:.4f}")
    print(f"   Omega比率: {results['omega_ratio']:.4f}")
    
    print(f"\n💼 交易分析:")
    print(f"   总交易次数: {results['total_trades']}")
    print(f"   盈利交易: {results['winning_trades']}")
    print(f"   亏损交易: {results['losing_trades']}")
    print(f"   胜率: {results['win_rate']:.2%}")
    print(f"   平均盈利: ${results['avg_win']:.2f}")
    print(f"   平均亏损: ${results['avg_loss']:.2f}")
    print(f"   盈亏比: {results['profit_factor']:.2f}")
    print(f"   期望收益: ${results['expectancy']:.2f}")
    print(f"   最大连续盈利: {results['max_consecutive_wins']}")
    print(f"   最大连续亏损: {results['max_consecutive_losses']}")
    
    print(f"\n📉 回撤分析:")
    print(f"   最大回撤: {results['max_drawdown']:.2%}")
    print(f"   最大回撤日期: {results['max_drawdown_date']}")
    print(f"   平均回撤持续时间: {results['avg_drawdown_duration']:.1f} 天")
    print(f"   最长回撤持续时间: {results['max_drawdown_duration']:.0f} 天")
    print(f"   平均恢复时间: {results['avg_recovery_time']:.1f} 天")
    print(f"   回撤期间占比: {results['time_in_drawdown']:.1%}")
    
    # 创建简化的可视化
    create_simple_visualization(price_data, equity_curve, results)
    
    return results

def create_simple_visualization(price_data, equity_curve, results):
    """创建简化的可视化图表"""
    print(f"\n📊 生成可视化图表...")
    
    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('📊 专业回测分析报告', fontsize=16, fontweight='bold')
    
    # 1. 权益曲线和回撤
    ax1 = axes[0, 0]
    equity_normalized = equity_curve / equity_curve.iloc[0]
    ax1.plot(equity_curve.index, equity_normalized, 
             color='blue', linewidth=2, label='权益曲线')
    
    # 回撤
    ax1_twin = ax1.twinx()
    drawdown = results['drawdown_series']
    ax1_twin.fill_between(drawdown.index, drawdown.values, 0, 
                         color='red', alpha=0.3, label='回撤')
    
    ax1.set_title('权益曲线与回撤')
    ax1.set_ylabel('累计收益倍数', color='blue')
    ax1_twin.set_ylabel('回撤', color='red')
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # 2. 收益分布
    ax2 = axes[0, 1]
    returns = results['daily_returns']
    ax2.hist(returns, bins=30, alpha=0.7, color='skyblue', density=True)
    ax2.axvline(returns.mean(), color='red', linestyle='--', 
                label=f'均值: {returns.mean():.4f}')
    ax2.axvline(results['var_95'], color='orange', linestyle='--', 
                label=f'95% VaR: {results["var_95"]:.4f}')
    ax2.set_title('日收益率分布')
    ax2.set_xlabel('日收益率')
    ax2.set_ylabel('密度')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 价格走势
    ax3 = axes[1, 0]
    ax3.plot(price_data.index, price_data['close'], 
             color='black', linewidth=1, label='价格')
    if 'fast_ma' in price_data.columns:
        ax3.plot(price_data.index, price_data['fast_ma'], 
                 color='orange', linewidth=1, label='快速MA')
    if 'slow_ma' in price_data.columns:
        ax3.plot(price_data.index, price_data['slow_ma'], 
                 color='purple', linewidth=1, label='慢速MA')
    
    ax3.set_title('价格走势与技术指标')
    ax3.set_ylabel('价格 (USDT)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 关键指标仪表盘
    ax4 = axes[1, 1]
    metrics = {
        '总收益率': f"{results['total_return']:.2%}",
        '年化收益': f"{results['annualized_return']:.2%}",
        '最大回撤': f"{results['max_drawdown']:.2%}",
        '夏普比率': f"{results['sharpe_ratio']:.3f}",
        '胜率': f"{results['win_rate']:.1%}",
        '盈亏比': f"{results['profit_factor']:.2f}"
    }
    
    y_pos = np.arange(len(metrics))
    colors = ['green' if '收益' in k or '夏普' in k or '胜率' in k or '盈亏' in k 
              else 'red' if '回撤' in k else 'blue' for k in metrics.keys()]
    
    for i, (key, value) in enumerate(metrics.items()):
        ax4.text(0.1, 0.9 - i*0.15, key, fontsize=12, fontweight='bold',
                transform=ax4.transAxes)
        ax4.text(0.7, 0.9 - i*0.15, value, fontsize=12, fontweight='bold',
                transform=ax4.transAxes, color=colors[i])
    
    ax4.set_title('关键指标')
    ax4.set_xlim(0, 1)
    ax4.set_ylim(0, 1)
    ax4.axis('off')
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = f"results/professional_demo_report_{timestamp}.png"
    os.makedirs('results', exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    print(f"✅ 可视化图表已保存: {save_path}")
    
    # 显示图表
    plt.show()
    
    return save_path

def main():
    """主函数"""
    print("🎯 专业回测系统演示")
    print("展示机构级别的回测分析能力")
    print("=" * 60)
    
    try:
        # 执行专业分析演示
        results = demo_professional_analysis()
        
        print(f"\n🎉 专业回测演示完成!")
        print(f"📊 本演示展示了以下专业功能:")
        print(f"   ✅ 49个专业分析指标")
        print(f"   ✅ 风险调整收益指标 (夏普、索提诺、卡尔马比率)")
        print(f"   ✅ 高级风险指标 (VaR, CVaR, 偏度, 峰度)")
        print(f"   ✅ 详细交易分析 (胜率、盈亏比、期望收益)")
        print(f"   ✅ 回撤深度分析 (持续时间、恢复时间)")
        print(f"   ✅ 专业可视化图表")
        
        print(f"\n🚀 与传统回测的区别:")
        print(f"   📈 传统回测: 只有基础收益率、最大回撤")
        print(f"   🏆 专业回测: 49个指标，机构级别分析深度")
        print(f"   📊 传统图表: 简单的价格和权益曲线")
        print(f"   🎨 专业图表: 多维度可视化，深度洞察")
        
        print(f"\n💡 专业回测的价值:")
        print(f"   🔍 深度风险分析: 识别隐藏风险")
        print(f"   📊 量化策略评估: 客观评价策略质量")
        print(f"   🎯 参数优化指导: 基于科学指标优化")
        print(f"   📈 投资决策支持: 提供决策依据")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
