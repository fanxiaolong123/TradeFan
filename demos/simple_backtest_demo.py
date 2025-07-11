"""
简单回测演示
使用简化策略进行回测，不依赖TA-Lib
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.simple_strategy import SimpleMovingAverageStrategy, SimpleTrendStrategy
from modules.utils import ConfigLoader
from modules.log_module import LogModule

class SimpleBacktester:
    """简单回测器"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0  # 持仓数量
        self.entry_price = 0  # 入场价格
        self.trades = []  # 交易记录
        self.equity_curve = []  # 权益曲线
        
    def run_backtest(self, data: pd.DataFrame, strategy, commission: float = 0.001):
        """运行回测"""
        print(f"开始回测 - 策略: {strategy.name}")
        print(f"数据期间: {data.index[0]} 到 {data.index[-1]}")
        print(f"数据条数: {len(data)}")
        
        # 生成交易信号
        signals = strategy.generate_signals(data)
        
        # 执行回测
        for i, row in signals.iterrows():
            current_price = row['close']
            signal = row['signal']
            
            # 记录当前权益
            current_equity = self.capital
            if self.position > 0:
                current_equity += self.position * current_price
            
            self.equity_curve.append({
                'timestamp': row['timestamp'] if 'timestamp' in row else i,
                'price': current_price,
                'equity': current_equity,
                'position': self.position,
                'signal': signal
            })
            
            # 处理交易信号
            if signal == 1 and self.position == 0:  # 买入信号
                # 计算可买入数量（扣除手续费）
                available_capital = self.capital * 0.95  # 保留5%作为缓冲
                self.position = available_capital / current_price
                self.entry_price = current_price
                self.capital -= self.position * current_price * (1 + commission)
                
                self.trades.append({
                    'timestamp': row['timestamp'] if 'timestamp' in row else i,
                    'type': 'buy',
                    'price': current_price,
                    'amount': self.position,
                    'capital': self.capital
                })
                
            elif signal == -1 and self.position > 0:  # 卖出信号
                # 卖出所有持仓
                sell_value = self.position * current_price * (1 - commission)
                self.capital += sell_value
                
                # 计算盈亏
                pnl = (current_price - self.entry_price) * self.position
                pnl_pct = (current_price - self.entry_price) / self.entry_price
                
                self.trades.append({
                    'timestamp': row['timestamp'] if 'timestamp' in row else i,
                    'type': 'sell',
                    'price': current_price,
                    'amount': self.position,
                    'capital': self.capital,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                self.position = 0
                self.entry_price = 0
        
        # 如果最后还有持仓，按最后价格计算
        if self.position > 0:
            final_price = signals.iloc[-1]['close']
            final_value = self.position * final_price
            total_equity = self.capital + final_value
        else:
            total_equity = self.capital
        
        return self.calculate_metrics(total_equity)
    
    def calculate_metrics(self, final_equity: float) -> dict:
        """计算回测指标"""
        # 基础指标
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 交易统计
        buy_trades = [t for t in self.trades if t['type'] == 'buy']
        sell_trades = [t for t in self.trades if t['type'] == 'sell']
        
        total_trades = len(sell_trades)
        winning_trades = len([t for t in sell_trades if t.get('pnl', 0) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 权益曲线分析
        equity_df = pd.DataFrame(self.equity_curve)
        if not equity_df.empty:
            equity_df['returns'] = equity_df['equity'].pct_change()
            max_drawdown = self.calculate_max_drawdown(equity_df['equity'])
        else:
            max_drawdown = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'equity_curve': equity_df
        }
    
    def calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """计算最大回撤"""
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        return abs(drawdown.min())
    
    def plot_results(self, results: dict, save_path: str = None):
        """绘制回测结果"""
        equity_df = results['equity_curve']
        
        if equity_df.empty:
            print("没有数据可绘制")
            return
        
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # 权益曲线
        axes[0].plot(equity_df.index, equity_df['equity'], label='Portfolio Value', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='r', linestyle='--', alpha=0.5, label='Initial Capital')
        axes[0].set_title('Portfolio Equity Curve')
        axes[0].set_ylabel('Value ($)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 价格和信号
        axes[1].plot(equity_df.index, equity_df['price'], label='Price', alpha=0.7)
        
        # 标记买卖点
        buy_signals = equity_df[equity_df['signal'] == 1]
        sell_signals = equity_df[equity_df['signal'] == -1]
        
        if not buy_signals.empty:
            axes[1].scatter(buy_signals.index, buy_signals['price'], 
                          color='green', marker='^', s=100, label='Buy Signal', zorder=5)
        
        if not sell_signals.empty:
            axes[1].scatter(sell_signals.index, sell_signals['price'], 
                          color='red', marker='v', s=100, label='Sell Signal', zorder=5)
        
        axes[1].set_title('Price and Trading Signals')
        axes[1].set_ylabel('Price')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # 持仓状态
        axes[2].fill_between(equity_df.index, 0, equity_df['position'], 
                           alpha=0.3, label='Position Size')
        axes[2].set_title('Position Size Over Time')
        axes[2].set_ylabel('Position')
        axes[2].set_xlabel('Time')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()

def generate_sample_data(symbol: str = "BTC/USDT", days: int = 30) -> pd.DataFrame:
    """生成示例数据"""
    print(f"生成 {symbol} 示例数据 ({days}天)")
    
    # 生成时间序列
    start_date = datetime.now() - timedelta(days=days)
    dates = pd.date_range(start_date, periods=days*24, freq='h')  # 小时数据
    
    # 生成价格数据（随机游走 + 趋势）
    np.random.seed(42)
    
    if symbol == "BTC/USDT":
        base_price = 50000
        volatility = 0.02
    elif symbol == "ETH/USDT":
        base_price = 3000
        volatility = 0.025
    else:
        base_price = 100
        volatility = 0.03
    
    # 添加一些趋势
    trend = np.sin(np.linspace(0, 4*np.pi, len(dates))) * 0.1
    noise = np.random.randn(len(dates)) * volatility
    
    price_changes = trend + noise
    prices = base_price * np.exp(np.cumsum(price_changes))
    
    # 生成OHLCV数据
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price * (1 + abs(np.random.randn() * 0.01))
        low = price * (1 - abs(np.random.randn() * 0.01))
        open_price = prices[i-1] if i > 0 else price
        volume = np.random.randint(100, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def main():
    """主函数"""
    print("🚀 简单回测演示")
    print("=" * 50)
    
    # 生成测试数据
    data = generate_sample_data("BTC/USDT", days=60)
    print(f"数据生成完成: {len(data)} 条记录")
    
    # 创建策略
    strategies = [
        SimpleMovingAverageStrategy(fast_period=12, slow_period=26),
        SimpleTrendStrategy(ma_period=20)
    ]
    
    results = {}
    
    # 对每个策略进行回测
    for strategy in strategies:
        print(f"\n{'='*50}")
        print(f"测试策略: {strategy.name}")
        
        # 创建回测器
        backtester = SimpleBacktester(initial_capital=10000)
        
        # 运行回测
        result = backtester.run_backtest(data, strategy)
        results[strategy.name] = result
        
        # 输出结果
        print(f"\n📊 回测结果:")
        print(f"初始资金: ${result['initial_capital']:,.2f}")
        print(f"最终权益: ${result['final_equity']:,.2f}")
        print(f"总收益率: {result['total_return']:.2%}")
        print(f"总交易次数: {result['total_trades']}")
        print(f"胜率: {result['win_rate']:.2%}")
        print(f"最大回撤: {result['max_drawdown']:.2%}")
        
        # 绘制结果
        save_path = f"results/backtest_{strategy.name.lower()}.png"
        os.makedirs("results", exist_ok=True)
        backtester.plot_results(result, save_path)
    
    # 策略比较
    print(f"\n{'='*50}")
    print("📈 策略比较")
    print(f"{'='*50}")
    
    comparison_data = []
    for name, result in results.items():
        comparison_data.append({
            'Strategy': name,
            'Return': f"{result['total_return']:.2%}",
            'Trades': result['total_trades'],
            'Win Rate': f"{result['win_rate']:.2%}",
            'Max DD': f"{result['max_drawdown']:.2%}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    print(comparison_df.to_string(index=False))
    
    print(f"\n🎯 演示完成！")
    print("结果文件保存在 results/ 目录")

if __name__ == "__main__":
    main()
