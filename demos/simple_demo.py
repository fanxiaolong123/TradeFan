#!/usr/bin/env python3
"""
自动交易系统简化演示
展示系统的核心功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def generate_simple_data(days=100):
    """生成简单的模拟数据"""
    print("📊 生成模拟交易数据...")
    
    # 生成时间序列
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 生成模拟价格数据
    np.random.seed(42)
    initial_price = 50000
    
    # 生成收益率序列
    returns = np.random.normal(0.001, 0.02, days)  # 平均0.1%日收益，2%波动率
    
    # 添加一些趋势
    trend = np.sin(np.arange(days) * 2 * np.pi / 30) * 0.005  # 30天周期的趋势
    returns += trend
    
    # 计算价格
    prices = [initial_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 创建DataFrame
    data = pd.DataFrame({
        'date': dates,
        'price': prices,
        'returns': [0] + list(np.diff(prices) / prices[:-1])
    })
    
    print(f"✅ 生成了{len(data)}天的数据")
    print(f"   价格范围: ${data['price'].min():.2f} - ${data['price'].max():.2f}")
    print(f"   平均日收益率: {data['returns'].mean()*100:.3f}%")
    
    return data

def simple_strategy(data):
    """简单的移动平均策略"""
    print("📈 运行简单移动平均策略...")
    
    # 计算移动平均线
    data['ma_short'] = data['price'].rolling(window=5).mean()  # 5日均线
    data['ma_long'] = data['price'].rolling(window=20).mean()  # 20日均线
    
    # 生成交易信号
    data['signal'] = 0
    data.loc[data['ma_short'] > data['ma_long'], 'signal'] = 1  # 买入信号
    data.loc[data['ma_short'] < data['ma_long'], 'signal'] = -1  # 卖出信号
    
    # 计算信号变化点
    data['position'] = data['signal'].shift(1).fillna(0)
    data['trade'] = data['signal'] - data['position']
    
    return data

def calculate_performance(data, initial_capital=10000):
    """计算策略性能"""
    print("📊 计算策略性能...")
    
    # 初始化
    capital = initial_capital
    position = 0  # 持仓数量
    portfolio_value = []
    trades = []
    
    for i, row in data.iterrows():
        if row['trade'] != 0:  # 有交易信号
            if row['trade'] > 0:  # 买入
                if position == 0:  # 当前空仓，可以买入
                    position = capital * 0.95 / row['price']  # 95%资金买入，留5%作为手续费缓冲
                    capital = capital * 0.05
                    trades.append({
                        'date': row['date'],
                        'action': 'BUY',
                        'price': row['price'],
                        'amount': position
                    })
            elif row['trade'] < 0:  # 卖出
                if position > 0:  # 当前有持仓，可以卖出
                    capital += position * row['price'] * 0.999  # 扣除0.1%手续费
                    trades.append({
                        'date': row['date'],
                        'action': 'SELL',
                        'price': row['price'],
                        'amount': position
                    })
                    position = 0
        
        # 计算当前组合价值
        current_value = capital + position * row['price']
        portfolio_value.append(current_value)
    
    data['portfolio_value'] = portfolio_value
    
    # 计算性能指标
    total_return = (portfolio_value[-1] / initial_capital - 1) * 100
    
    # 计算最大回撤
    peak = np.maximum.accumulate(portfolio_value)
    drawdown = (portfolio_value - peak) / peak
    max_drawdown = np.min(drawdown) * 100
    
    # 计算夏普比率
    portfolio_returns = np.diff(portfolio_value) / portfolio_value[:-1]
    if len(portfolio_returns) > 0 and np.std(portfolio_returns) > 0:
        sharpe_ratio = np.mean(portfolio_returns) / np.std(portfolio_returns) * np.sqrt(252)
    else:
        sharpe_ratio = 0
    
    print(f"✅ 性能计算完成:")
    print(f"   总收益率: {total_return:.2f}%")
    print(f"   最大回撤: {max_drawdown:.2f}%")
    print(f"   夏普比率: {sharpe_ratio:.3f}")
    print(f"   交易次数: {len(trades)}")
    
    return data, trades, {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'num_trades': len(trades)
    }

def create_charts(data, trades, performance):
    """创建可视化图表"""
    print("📊 生成可视化图表...")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('自动交易系统演示结果', fontsize=16, fontweight='bold')
    
    # 1. 价格和移动平均线
    axes[0, 0].plot(data['date'], data['price'], label='价格', linewidth=1, alpha=0.8)
    axes[0, 0].plot(data['date'], data['ma_short'], label='5日均线', linewidth=1)
    axes[0, 0].plot(data['date'], data['ma_long'], label='20日均线', linewidth=1)
    
    # 标记买卖点
    buy_signals = data[data['trade'] > 0]
    sell_signals = data[data['trade'] < 0]
    
    if len(buy_signals) > 0:
        axes[0, 0].scatter(buy_signals['date'], buy_signals['price'], 
                          color='green', marker='^', s=50, label='买入', zorder=5)
    if len(sell_signals) > 0:
        axes[0, 0].scatter(sell_signals['date'], sell_signals['price'], 
                          color='red', marker='v', s=50, label='卖出', zorder=5)
    
    axes[0, 0].set_title('价格走势与交易信号')
    axes[0, 0].set_ylabel('价格 ($)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. 组合价值曲线
    axes[0, 1].plot(data['date'], data['portfolio_value'], linewidth=2, color='blue')
    axes[0, 1].axhline(y=10000, color='red', linestyle='--', alpha=0.7, label='初始资金')
    axes[0, 1].set_title('组合价值曲线')
    axes[0, 1].set_ylabel('价值 ($)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. 收益率分布
    returns = data['returns'].dropna()
    axes[1, 0].hist(returns, bins=20, alpha=0.7, color='green', edgecolor='black')
    axes[1, 0].axvline(x=returns.mean(), color='red', linestyle='--', label=f'均值: {returns.mean()*100:.3f}%')
    axes[1, 0].set_title('日收益率分布')
    axes[1, 0].set_xlabel('日收益率')
    axes[1, 0].set_ylabel('频次')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. 性能指标
    metrics = [
        f"总收益率: {performance['total_return']:.2f}%",
        f"最大回撤: {performance['max_drawdown']:.2f}%",
        f"夏普比率: {performance['sharpe_ratio']:.3f}",
        f"交易次数: {performance['num_trades']}"
    ]
    
    axes[1, 1].text(0.1, 0.8, '\\n'.join(metrics), transform=axes[1, 1].transAxes,
                    fontsize=12, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    axes[1, 1].set_title('性能指标')
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    
    # 保存图表
    os.makedirs('results', exist_ok=True)
    chart_path = f"results/simple_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"📊 图表已保存至: {chart_path}")
    
    plt.show()

def main():
    """主函数"""
    print("="*60)
    print("🚀 自动交易系统简化演示")
    print("="*60)
    
    try:
        # 1. 生成模拟数据
        data = generate_simple_data(days=100)
        
        # 2. 运行策略
        data = simple_strategy(data)
        
        # 3. 计算性能
        data, trades, performance = calculate_performance(data)
        
        # 4. 创建图表
        create_charts(data, trades, performance)
        
        # 5. 保存结果
        results_path = f"results/simple_demo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        data.to_csv(results_path, index=False)
        print(f"📄 详细数据已保存至: {results_path}")
        
        if trades:
            trades_path = f"results/simple_demo_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(trades).to_csv(trades_path, index=False)
            print(f"📄 交易记录已保存至: {trades_path}")
        
        print("\n" + "="*60)
        print("✅ 演示完成！")
        print("💡 这是一个简化的演示，展示了自动交易系统的基本功能")
        print("💡 实际系统具有更复杂的策略、风险控制和执行机制")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
