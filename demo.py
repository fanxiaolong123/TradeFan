#!/usr/bin/env python3
"""
自动交易系统演示脚本
使用模拟数据展示系统功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.strategy_module import TrendFollowingStrategy
from modules.risk_control_module import RiskControlModule
from modules.execution_module import ExecutionModule
from modules.utils import DataProcessor

def generate_mock_data(symbol="BTC/USDT", days=365, start_price=50000):
    """生成模拟的价格数据"""
    print(f"📊 生成{symbol}模拟数据...")
    
    # 生成时间序列
    start_date = datetime.now() - timedelta(days=days)
    dates = pd.date_range(start=start_date, periods=days*24, freq='h')
    
    # 生成价格数据（随机游走 + 趋势）
    np.random.seed(42)  # 固定随机种子，确保结果可重现
    
    # 基础随机游走
    returns = np.random.normal(0, 0.02, len(dates))
    
    # 添加趋势成分
    trend = np.sin(np.arange(len(dates)) * 2 * np.pi / (30 * 24)) * 0.01
    returns += trend
    
    # 计算价格
    prices = [start_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成OHLCV数据
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 模拟开高低收
        open_price = price
        high_price = price * (1 + abs(np.random.normal(0, 0.005)))
        low_price = price * (1 - abs(np.random.normal(0, 0.005)))
        close_price = price * (1 + np.random.normal(0, 0.002))
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    print(f"✅ 生成了{len(df)}条数据，价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
    return df

def run_strategy_demo():
    """运行策略演示"""
    print("\n" + "="*60)
    print("🚀 自动交易系统演示")
    print("="*60)
    
    # 1. 生成模拟数据
    btc_data = generate_mock_data("BTC/USDT", days=180, start_price=50000)
    eth_data = generate_mock_data("ETH/USDT", days=180, start_price=3000)
    
    # 2. 初始化策略
    print("\n📈 初始化趋势跟踪策略...")
    strategy_params = {
        'fast_ma': 20,
        'slow_ma': 50,
        'adx_period': 14,
        'adx_threshold': 25,
        'donchian_period': 20
    }
    
    btc_strategy = TrendFollowingStrategy(strategy_params)
    eth_strategy = TrendFollowingStrategy(strategy_params)
    
    # 3. 初始化风险控制
    print("🛡️ 初始化风险控制模块...")
    risk_config = {
        'max_position_size': 0.1,
        'max_total_position': 0.8,
        'max_drawdown': 0.2,
        'stop_loss': 0.02,
        'take_profit': 0.04,
        'initial_capital': 10000
    }
    risk_control = RiskControlModule(risk_config)
    
    # 4. 初始化执行模块
    print("⚡ 初始化执行模块...")
    execution_config = {'commission': 0.001}
    execution = ExecutionModule(execution_config)
    
    # 5. 运行回测
    print("\n🔄 开始策略回测...")
    
    # 存储交易记录
    trades = []
    portfolio_value = [risk_config['initial_capital']]
    dates = []
    
    # 模拟交易过程
    for i in range(100, len(btc_data)):  # 从第100个数据点开始，确保有足够的历史数据
        current_date = btc_data.index[i]
        dates.append(current_date)
        
        # 获取当前数据切片
        btc_slice = btc_data.iloc[:i+1]
        eth_slice = eth_data.iloc[:i+1]
        
        # 生成交易信号
        btc_signals = btc_strategy.generate_signals(btc_slice)
        eth_signals = eth_strategy.generate_signals(eth_slice)
        
        current_value = portfolio_value[-1]
        
        # 处理BTC信号
        if len(btc_signals) > 0:
            latest_btc_signal = btc_signals.iloc[-1]
            if latest_btc_signal['signal'] != 0:
                # 风险检查
                position_size = 0.05  # 5%仓位
                can_trade, reason, adjusted_size = risk_control.check_position_size(
                    "BTC/USDT", position_size, btc_slice['close'].iloc[-1]
                )
                
                if can_trade:
                    trade_amount = current_value * adjusted_size
                    price = btc_slice['close'].iloc[-1]
                    
                    if latest_btc_signal['signal'] > 0:  # 买入信号
                        trades.append({
                            'timestamp': current_date,
                            'symbol': 'BTC/USDT',
                            'side': 'buy',
                            'amount': trade_amount / price,
                            'price': price,
                            'value': trade_amount
                        })
                        current_value -= trade_amount * (1 + 0.001)  # 扣除手续费
                    
                    elif latest_btc_signal['signal'] < 0:  # 卖出信号
                        trades.append({
                            'timestamp': current_date,
                            'symbol': 'BTC/USDT',
                            'side': 'sell',
                            'amount': trade_amount / price,
                            'price': price,
                            'value': trade_amount
                        })
                        current_value += trade_amount * (1 - 0.001)  # 扣除手续费
        
        # 处理ETH信号（类似逻辑）
        if len(eth_signals) > 0:
            latest_eth_signal = eth_signals.iloc[-1]
            if latest_eth_signal['signal'] != 0:
                position_size = 0.05
                can_trade, reason, adjusted_size = risk_control.check_position_size(
                    "ETH/USDT", position_size, eth_slice['close'].iloc[-1]
                )
                
                if can_trade:
                    trade_amount = current_value * adjusted_size
                    price = eth_slice['close'].iloc[-1]
                    
                    if latest_eth_signal['signal'] > 0:
                        trades.append({
                            'timestamp': current_date,
                            'symbol': 'ETH/USDT',
                            'side': 'buy',
                            'amount': trade_amount / price,
                            'price': price,
                            'value': trade_amount
                        })
                        current_value -= trade_amount * (1 + 0.001)
                    
                    elif latest_eth_signal['signal'] < 0:
                        trades.append({
                            'timestamp': current_date,
                            'symbol': 'ETH/USDT',
                            'side': 'sell',
                            'amount': trade_amount / price,
                            'price': price,
                            'value': trade_amount
                        })
                        current_value += trade_amount * (1 - 0.001)
        
        portfolio_value.append(current_value)
    
    # 6. 分析结果
    print("\n📊 回测结果分析...")
    
    # 创建结果DataFrame
    results_df = pd.DataFrame({
        'timestamp': dates,
        'portfolio_value': portfolio_value[1:]  # 去掉初始值
    })
    results_df.set_index('timestamp', inplace=True)
    
    # 计算性能指标
    returns = DataProcessor.calculate_returns(results_df['portfolio_value'])
    total_return = (results_df['portfolio_value'].iloc[-1] / risk_config['initial_capital'] - 1) * 100
    sharpe_ratio = DataProcessor.calculate_sharpe_ratio(returns)
    max_drawdown = DataProcessor.calculate_max_drawdown(results_df['portfolio_value']) * 100
    
    # 交易统计
    trades_df = pd.DataFrame(trades)
    total_trades = len(trades_df)
    buy_trades = len(trades_df[trades_df['side'] == 'buy'])
    sell_trades = len(trades_df[trades_df['side'] == 'sell'])
    
    # 打印结果
    print(f"\n{'='*60}")
    print("📈 回测结果摘要")
    print(f"{'='*60}")
    print(f"📅 回测期间: {results_df.index[0].strftime('%Y-%m-%d')} 至 {results_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"💰 初始资金: ${risk_config['initial_capital']:,.2f}")
    print(f"💰 最终资金: ${results_df['portfolio_value'].iloc[-1]:,.2f}")
    print(f"📊 总收益率: {total_return:.2f}%")
    print(f"📊 夏普比率: {sharpe_ratio:.4f}")
    print(f"📊 最大回撤: {max_drawdown:.2f}%")
    print(f"🔄 总交易次数: {total_trades}")
    print(f"🔄 买入次数: {buy_trades}")
    print(f"🔄 卖出次数: {sell_trades}")
    
    # 7. 生成图表
    print("\n📊 生成可视化图表...")
    
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('自动交易系统回测结果', fontsize=16, fontweight='bold')
    
    # 资金曲线
    axes[0, 0].plot(results_df.index, results_df['portfolio_value'], linewidth=2, color='blue')
    axes[0, 0].axhline(y=risk_config['initial_capital'], color='red', linestyle='--', alpha=0.7, label='初始资金')
    axes[0, 0].set_title('资金曲线')
    axes[0, 0].set_ylabel('资金 ($)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 收益率分布
    axes[0, 1].hist(returns, bins=30, alpha=0.7, color='green', edgecolor='black')
    axes[0, 1].set_title('收益率分布')
    axes[0, 1].set_xlabel('日收益率')
    axes[0, 1].set_ylabel('频次')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 价格走势对比
    axes[1, 0].plot(btc_data.index[-len(results_df):], btc_data['close'].iloc[-len(results_df):], 
                    label='BTC/USDT', alpha=0.8)
    axes[1, 0].plot(eth_data.index[-len(results_df):], eth_data['close'].iloc[-len(results_df):], 
                    label='ETH/USDT', alpha=0.8)
    axes[1, 0].set_title('价格走势')
    axes[1, 0].set_ylabel('价格 ($)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 交易分布
    if total_trades > 0:
        symbol_counts = trades_df['symbol'].value_counts()
        axes[1, 1].pie(symbol_counts.values, labels=symbol_counts.index, autopct='%1.1f%%')
        axes[1, 1].set_title('交易分布')
    else:
        axes[1, 1].text(0.5, 0.5, '无交易记录', ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title('交易分布')
    
    plt.tight_layout()
    
    # 保存图表
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    chart_path = os.path.join(results_dir, f"demo_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"📊 图表已保存至: {chart_path}")
    
    # 显示图表
    plt.show()
    
    # 8. 保存详细结果
    if total_trades > 0:
        trades_path = os.path.join(results_dir, f"demo_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        trades_df.to_csv(trades_path, index=False)
        print(f"📄 交易记录已保存至: {trades_path}")
    
    portfolio_path = os.path.join(results_dir, f"demo_portfolio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    results_df.to_csv(portfolio_path)
    print(f"📄 资金曲线已保存至: {portfolio_path}")
    
    print(f"\n{'='*60}")
    print("✅ 演示完成！")
    print("💡 提示：这是使用模拟数据的演示，实际使用时需要配置真实的API密钥")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        run_strategy_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
