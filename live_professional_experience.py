#!/usr/bin/env python3
"""
实时专业回测体验
使用真实数据和策略进行专业分析
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

def live_professional_experience():
    """实时专业回测体验"""
    print("🚀 实时专业回测体验")
    print("使用真实BTC数据和优化策略参数")
    print("=" * 60)
    
    # 1. 获取真实数据
    print("📊 获取真实BTC市场数据...")
    data_source = RealDataSource()
    
    try:
        price_data = data_source.get_data(
            symbol='BTCUSDT',
            timeframe='1d',
            start_date='2024-01-01',
            end_date='2024-06-30',  # 6个月数据
            source='binance'
        )
        
        df = price_data.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        print(f"✅ 真实数据获取成功: {len(df)} 条记录")
        print(f"   时间范围: {df.index.min().strftime('%Y-%m-%d')} 到 {df.index.max().strftime('%Y-%m-%d')}")
        print(f"   价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        print(f"   期间涨幅: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1):.2%}")
        
    except Exception as e:
        print(f"❌ 数据获取失败: {str(e)}")
        return False
    
    # 2. 创建优化策略
    print(f"\n📈 创建优化的移动平均策略...")
    
    # 使用优化参数
    strategy = TrendMABreakoutStrategy(
        fast_ma=12,  # 优化后的快速MA
        slow_ma=26,  # 优化后的慢速MA
        rsi_period=14,
        rsi_overbought=75,  # 更严格的超买线
        rsi_oversold=25,    # 更严格的超卖线
        ma_type='EMA'       # 使用EMA
    )
    
    print(f"✅ 策略参数: {strategy.params}")
    
    # 3. 计算指标和信号
    print(f"\n🔧 计算技术指标和交易信号...")
    
    df_indicators = strategy.calculate_indicators(df)
    signals = strategy.generate_signals(df_indicators)
    
    buy_signals = len(signals[signals['signal'] == 'buy'])
    sell_signals = len(signals[signals['signal'] == 'sell'])
    
    print(f"✅ 技术指标计算完成")
    print(f"   买入信号: {buy_signals} 个")
    print(f"   卖出信号: {sell_signals} 个")
    
    # 4. 执行回测
    print(f"\n🔄 执行专业回测...")
    
    initial_capital = 100000
    equity_curve, trades = execute_realistic_backtest(df_indicators, signals, initial_capital)
    
    print(f"✅ 回测执行完成")
    print(f"   交易次数: {len(trades)}")
    print(f"   初始资金: ${initial_capital:,.2f}")
    print(f"   最终权益: ${equity_curve.iloc[-1]:,.2f}")
    print(f"   总收益: ${equity_curve.iloc[-1] - initial_capital:,.2f}")
    
    # 5. 专业分析
    print(f"\n🔍 执行专业分析...")
    
    analyzer = ProfessionalBacktestAnalyzer()
    
    # 计算基准 (买入持有)
    benchmark = df['close'] / df['close'].iloc[0] * initial_capital
    
    results = analyzer.analyze_backtest_results(
        equity_curve=equity_curve,
        trades=trades,
        benchmark=benchmark
    )
    
    print(f"✅ 专业分析完成，共 {len(results)} 个指标")
    
    # 6. 生成专业报告
    print(f"\n📊 生成专业可视化报告...")
    
    create_live_professional_report(df_indicators, equity_curve, trades, results, benchmark)
    
    # 7. 详细分析解读
    print_detailed_analysis(results)
    
    # 8. 投资建议
    generate_investment_advice(results)
    
    return True

def execute_realistic_backtest(data, signals, initial_capital):
    """执行更真实的回测"""
    capital = initial_capital
    position = 0
    trades = []
    equity_curve = []
    
    # 交易成本
    commission_rate = 0.001  # 0.1% 手续费
    slippage_rate = 0.0005   # 0.05% 滑点
    
    combined = data.join(signals[['signal']], how='left')
    combined['signal'] = combined['signal'].fillna('hold')
    
    for i, (date, row) in enumerate(combined.iterrows()):
        current_price = row['close']
        signal = row['signal']
        
        # 执行交易
        if signal == 'buy' and position == 0 and capital > 1000:  # 最小交易金额
            # 买入
            total_cost = capital
            commission = total_cost * commission_rate
            slippage = total_cost * slippage_rate
            actual_cost = total_cost + commission + slippage
            
            if actual_cost <= capital:
                shares = (capital - commission - slippage) / current_price
                position = shares
                capital = 0
                
                trades.append({
                    'entry_time': date,
                    'entry_price': current_price,
                    'side': 'buy',
                    'shares': shares,
                    'commission': commission,
                    'slippage': slippage
                })
                
        elif signal == 'sell' and position > 0:
            # 卖出
            gross_proceeds = position * current_price
            commission = gross_proceeds * commission_rate
            slippage = gross_proceeds * slippage_rate
            net_proceeds = gross_proceeds - commission - slippage
            
            capital = net_proceeds
            
            # 更新交易记录
            if trades:
                entry_cost = trades[-1]['shares'] * trades[-1]['entry_price']
                pnl = net_proceeds - entry_cost
                
                trades[-1].update({
                    'exit_time': date,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'gross_pnl': gross_proceeds - entry_cost,
                    'total_commission': trades[-1]['commission'] + commission,
                    'total_slippage': trades[-1]['slippage'] + slippage
                })
            
            position = 0
        
        # 计算当前权益
        current_equity = capital + (position * current_price if position > 0 else 0)
        equity_curve.append(current_equity)
    
    # 处理最后的持仓
    if position > 0:
        final_price = combined['close'].iloc[-1]
        gross_proceeds = position * final_price
        commission = gross_proceeds * commission_rate
        slippage = gross_proceeds * slippage_rate
        net_proceeds = gross_proceeds - commission - slippage
        
        if trades:
            entry_cost = trades[-1]['shares'] * trades[-1]['entry_price']
            pnl = net_proceeds - entry_cost
            
            trades[-1].update({
                'exit_time': combined.index[-1],
                'exit_price': final_price,
                'pnl': pnl,
                'gross_pnl': gross_proceeds - entry_cost,
                'total_commission': trades[-1]['commission'] + commission,
                'total_slippage': trades[-1]['slippage'] + slippage
            })
    
    equity_series = pd.Series(equity_curve, index=combined.index)
    trades_df = pd.DataFrame(trades)
    
    return equity_series, trades_df

def create_live_professional_report(price_data, equity_curve, trades, results, benchmark):
    """创建实时专业报告"""
    fig, axes = plt.subplots(3, 2, figsize=(20, 16))
    fig.suptitle('🏆 TradeFan专业回测分析报告 - 真实BTC数据', fontsize=18, fontweight='bold')
    
    # 1. 权益曲线对比
    ax1 = axes[0, 0]
    equity_normalized = equity_curve / equity_curve.iloc[0]
    benchmark_normalized = benchmark / benchmark.iloc[0]
    
    ax1.plot(equity_curve.index, equity_normalized, 
             color='blue', linewidth=2, label='策略权益', alpha=0.8)
    ax1.plot(benchmark.index, benchmark_normalized, 
             color='orange', linewidth=2, label='买入持有', alpha=0.8)
    
    ax1.set_title('📈 策略 vs 基准表现', fontsize=14, fontweight='bold')
    ax1.set_ylabel('累计收益倍数')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 回撤分析
    ax2 = axes[0, 1]
    drawdown = results['drawdown_series']
    ax2.fill_between(drawdown.index, drawdown.values, 0, 
                     color='red', alpha=0.6, label='回撤')
    ax2.plot(drawdown.index, drawdown.values, color='darkred', linewidth=1)
    
    # 标记最大回撤
    max_dd_date = results['max_drawdown_date']
    max_dd_value = results['max_drawdown']
    ax2.scatter([max_dd_date], [-max_dd_value], 
                color='red', s=100, zorder=5)
    ax2.text(max_dd_date, -max_dd_value-0.02, 
             f'最大回撤\n{max_dd_value:.1%}', 
             ha='center', va='top', fontsize=10, 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax2.set_title('📉 回撤分析', fontsize=14, fontweight='bold')
    ax2.set_ylabel('回撤幅度')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 价格和交易信号
    ax3 = axes[1, 0]
    ax3.plot(price_data.index, price_data['close'], 
             color='black', linewidth=1.5, label='BTC价格', alpha=0.8)
    ax3.plot(price_data.index, price_data['fast_ma'], 
             color='blue', linewidth=1, label='快速EMA(12)', alpha=0.7)
    ax3.plot(price_data.index, price_data['slow_ma'], 
             color='red', linewidth=1, label='慢速EMA(26)', alpha=0.7)
    
    # 标记交易点
    if not trades.empty:
        for _, trade in trades.iterrows():
            if 'entry_time' in trade and pd.notna(trade['entry_time']):
                ax3.scatter(trade['entry_time'], trade['entry_price'], 
                           color='green', marker='^', s=100, zorder=5)
            if 'exit_time' in trade and pd.notna(trade['exit_time']):
                ax3.scatter(trade['exit_time'], trade['exit_price'], 
                           color='red', marker='v', s=100, zorder=5)
    
    ax3.set_title('💹 BTC价格走势与交易信号', fontsize=14, fontweight='bold')
    ax3.set_ylabel('价格 (USDT)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. 收益分布
    ax4 = axes[1, 1]
    returns = results['daily_returns']
    ax4.hist(returns, bins=30, alpha=0.7, color='skyblue', density=True, edgecolor='white')
    
    # 添加统计线
    ax4.axvline(returns.mean(), color='green', linestyle='--', 
                label=f'均值: {returns.mean():.4f}')
    ax4.axvline(results['var_95'], color='red', linestyle='--', 
                label=f'95% VaR: {results["var_95"]:.4f}')
    ax4.axvline(0, color='black', linestyle='-', alpha=0.5)
    
    ax4.set_title('📊 日收益率分布', fontsize=14, fontweight='bold')
    ax4.set_xlabel('日收益率')
    ax4.set_ylabel('密度')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 5. 关键指标仪表盘
    ax5 = axes[2, 0]
    metrics = {
        '总收益率': f"{results['total_return']:.2%}",
        '年化收益率': f"{results['annualized_return']:.2%}",
        '最大回撤': f"{results['max_drawdown']:.2%}",
        '夏普比率': f"{results['sharpe_ratio']:.3f}",
        '索提诺比率': f"{results['sortino_ratio']:.3f}",
        '胜率': f"{results['win_rate']:.1%}",
        '盈亏比': f"{results['profit_factor']:.2f}",
        '期望收益': f"${results['expectancy']:.2f}"
    }
    
    y_positions = np.linspace(0.9, 0.1, len(metrics))
    colors = ['green', 'green', 'red', 'blue', 'blue', 'orange', 'orange', 'purple']
    
    for i, ((key, value), color) in enumerate(zip(metrics.items(), colors)):
        ax5.text(0.1, y_positions[i], key, fontsize=12, fontweight='bold',
                transform=ax5.transAxes, ha='left')
        ax5.text(0.7, y_positions[i], value, fontsize=12, fontweight='bold',
                transform=ax5.transAxes, ha='right', color=color)
    
    ax5.set_title('📊 关键指标仪表盘', fontsize=14, fontweight='bold')
    ax5.set_xlim(0, 1)
    ax5.set_ylim(0, 1)
    ax5.axis('off')
    
    # 6. 月度收益
    ax6 = axes[2, 1]
    monthly_returns = results['monthly_returns']
    
    if len(monthly_returns) > 0:
        months = [f"{date.strftime('%Y-%m')}" for date in monthly_returns.index]
        values = monthly_returns.values
        colors_monthly = ['green' if v > 0 else 'red' for v in values]
        
        bars = ax6.bar(range(len(months)), values, color=colors_monthly, alpha=0.7)
        ax6.set_xticks(range(len(months)))
        ax6.set_xticklabels(months, rotation=45)
        ax6.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1%}', ha='center', 
                    va='bottom' if height > 0 else 'top', fontsize=10)
    
    ax6.set_title('📅 月度收益表现', fontsize=14, fontweight='bold')
    ax6.set_ylabel('月收益率')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = f"results/live_professional_report_{timestamp}.png"
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    
    print(f"✅ 专业报告已保存: {save_path}")
    
    return save_path

def print_detailed_analysis(results):
    """打印详细分析"""
    print(f"\n" + "=" * 60)
    print(f"📊 详细专业分析报告")
    print(f"=" * 60)
    
    print(f"\n🎯 收益表现分析:")
    print(f"   总收益率: {results['total_return']:.2%}")
    print(f"   年化收益率: {results['annualized_return']:.2%}")
    print(f"   最佳单日: {results['best_day']:.2%}")
    print(f"   最差单日: {results['worst_day']:.2%}")
    print(f"   正收益天数: {results['positive_days_ratio']:.1%}")
    
    print(f"\n⚠️ 风险控制分析:")
    print(f"   最大回撤: {results['max_drawdown']:.2%}")
    print(f"   年化波动率: {results['annualized_volatility']:.2%}")
    print(f"   95% VaR: {results['var_95']:.3f} (95%概率下日亏损不超过{abs(results['var_95']):.1%})")
    print(f"   99% VaR: {results['var_99']:.3f} (99%概率下日亏损不超过{abs(results['var_99']):.1%})")
    print(f"   下行偏差: {results['downside_deviation']:.2%}")
    
    print(f"\n📈 风险调整收益:")
    print(f"   夏普比率: {results['sharpe_ratio']:.4f}")
    print(f"   索提诺比率: {results['sortino_ratio']:.4f}")
    print(f"   卡尔马比率: {results['calmar_ratio']:.4f}")
    
    print(f"\n💼 交易效率分析:")
    print(f"   总交易次数: {results['total_trades']}")
    print(f"   胜率: {results['win_rate']:.1%}")
    print(f"   盈亏比: {results['profit_factor']:.2f}")
    print(f"   期望收益: ${results['expectancy']:.2f}")
    print(f"   最大连续盈利: {results['max_consecutive_wins']} 笔")
    print(f"   最大连续亏损: {results['max_consecutive_losses']} 笔")

def generate_investment_advice(results):
    """生成投资建议"""
    print(f"\n" + "=" * 60)
    print(f"💡 专业投资建议")
    print(f"=" * 60)
    
    # 综合评分
    score = 0
    
    # 收益评分
    if results['annualized_return'] > 0.2:
        score += 2
    elif results['annualized_return'] > 0.1:
        score += 1
    
    # 风险评分
    if results['max_drawdown'] < 0.15:
        score += 2
    elif results['max_drawdown'] < 0.25:
        score += 1
    
    # 夏普比率评分
    if results['sharpe_ratio'] > 1.0:
        score += 2
    elif results['sharpe_ratio'] > 0.5:
        score += 1
    
    # 胜率评分
    if results['win_rate'] > 0.6:
        score += 1
    
    print(f"📊 策略综合评分: {score}/7")
    
    if score >= 6:
        rating = "🏆 优秀"
        advice = "该策略表现优秀，建议增加投资比例或扩大资金规模。"
    elif score >= 4:
        rating = "✅ 良好"
        advice = "该策略表现良好，可以考虑实盘应用，但建议先小资金测试。"
    elif score >= 2:
        rating = "⚠️ 一般"
        advice = "该策略表现一般，建议优化参数或改进策略逻辑后再使用。"
    else:
        rating = "❌ 较差"
        advice = "该策略表现较差，不建议实盘使用，需要重新设计。"
    
    print(f"🎯 策略评级: {rating}")
    print(f"💭 投资建议: {advice}")
    
    # 具体改进建议
    print(f"\n🔧 改进建议:")
    
    if results['max_drawdown'] > 0.2:
        print(f"   • 回撤过大({results['max_drawdown']:.1%})，建议加强止损机制")
    
    if results['sharpe_ratio'] < 0.5:
        print(f"   • 夏普比率偏低({results['sharpe_ratio']:.3f})，建议优化风险管理")
    
    if results['win_rate'] < 0.5:
        print(f"   • 胜率偏低({results['win_rate']:.1%})，建议改进入场条件")
    
    if results['profit_factor'] < 1.5:
        print(f"   • 盈亏比偏低({results['profit_factor']:.2f})，建议优化出场策略")
    
    print(f"\n🚀 下一步行动:")
    print(f"   1. 基于分析结果优化策略参数")
    print(f"   2. 在不同市场环境下测试策略稳定性")
    print(f"   3. 考虑与其他策略组合降低风险")
    print(f"   4. 准备小资金实盘验证")

if __name__ == "__main__":
    live_professional_experience()
