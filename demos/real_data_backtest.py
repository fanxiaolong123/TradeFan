"""
真实数据回测脚本
从币安获取历史数据进行回测
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ccxt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.simple_strategy import SimpleMovingAverageStrategy, SimpleTrendStrategy

class RealDataBacktester:
    """真实数据回测器"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.exchange = ccxt.binance({
            'sandbox': False,  # 使用真实数据
            'enableRateLimit': True,
        })
        
    def fetch_historical_data(self, symbol: str, timeframe: str = '1h', 
                            days: int = 30) -> pd.DataFrame:
        """获取历史数据"""
        print(f"获取 {symbol} 历史数据...")
        
        try:
            # 计算时间范围
            since = self.exchange.milliseconds() - days * 24 * 60 * 60 * 1000
            
            # 获取OHLCV数据
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since)
            
            # 转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            print(f"✓ 获取到 {len(df)} 条数据")
            return df
            
        except Exception as e:
            print(f"✗ 数据获取失败: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, data: pd.DataFrame, strategy, symbol: str):
        """运行回测"""
        if data.empty:
            print("没有数据可回测")
            return None
            
        print(f"开始回测 {symbol} - 策略: {strategy.name}")
        
        # 重置数据索引用于策略计算
        data_reset = data.reset_index()
        
        # 生成交易信号
        signals = strategy.generate_signals(data_reset)
        
        # 计算回测结果
        results = self._calculate_backtest_results(signals, symbol)
        
        return results
    
    def _calculate_backtest_results(self, signals: pd.DataFrame, symbol: str):
        """计算回测结果"""
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = []
        
        for i, row in signals.iterrows():
            current_price = row['close']
            signal = row['signal']
            
            # 计算当前权益
            current_equity = capital
            if position > 0:
                current_equity += position * current_price
            
            equity_curve.append({
                'timestamp': row.get('timestamp', i),
                'price': current_price,
                'equity': current_equity,
                'position': position,
                'signal': signal
            })
            
            # 处理交易信号
            if signal == 1 and position == 0:  # 买入
                position = capital * 0.95 / current_price  # 95%资金买入
                entry_price = current_price
                capital -= position * current_price * 1.001  # 扣除手续费
                
                trades.append({
                    'timestamp': row.get('timestamp', i),
                    'type': 'buy',
                    'price': current_price,
                    'amount': position
                })
                
            elif signal == -1 and position > 0:  # 卖出
                sell_value = position * current_price * 0.999  # 扣除手续费
                pnl = (current_price - entry_price) * position
                pnl_pct = (current_price - entry_price) / entry_price
                
                capital += sell_value
                
                trades.append({
                    'timestamp': row.get('timestamp', i),
                    'type': 'sell',
                    'price': current_price,
                    'amount': position,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                position = 0
                entry_price = 0
        
        # 计算最终权益
        if position > 0:
            final_price = signals.iloc[-1]['close']
            final_equity = capital + position * final_price
        else:
            final_equity = capital
        
        # 计算指标
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell']
        
        total_trades = len(sell_trades)
        winning_trades = len([t for t in sell_trades if t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 计算最大回撤
        equity_df = pd.DataFrame(equity_curve)
        max_drawdown = 0
        if not equity_df.empty:
            peak = equity_df['equity'].expanding().max()
            drawdown = (equity_df['equity'] - peak) / peak
            max_drawdown = abs(drawdown.min())
        
        return {
            'symbol': symbol,
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'trades': trades,
            'equity_curve': equity_df,
            'signals': signals
        }
    
    def plot_results(self, results: dict, save_path: str = None):
        """绘制回测结果"""
        if not results or results['equity_curve'].empty:
            print("没有数据可绘制")
            return
        
        equity_df = results['equity_curve']
        signals = results['signals']
        symbol = results['symbol']
        
        fig, axes = plt.subplots(4, 1, figsize=(15, 12))
        
        # 1. 价格和移动平均线
        axes[0].plot(signals.index, signals['close'], label='Price', alpha=0.8, linewidth=1)
        
        if 'sma_fast' in signals.columns:
            axes[0].plot(signals.index, signals['sma_fast'], label='Fast MA', alpha=0.7)
            axes[0].plot(signals.index, signals['sma_slow'], label='Slow MA', alpha=0.7)
        elif 'ma' in signals.columns:
            axes[0].plot(signals.index, signals['ma'], label='MA', alpha=0.7)
        
        # 标记买卖点
        buy_signals = signals[signals['signal'] == 1]
        sell_signals = signals[signals['signal'] == -1]
        
        if not buy_signals.empty:
            axes[0].scatter(buy_signals.index, buy_signals['close'], 
                          color='green', marker='^', s=100, label='Buy', zorder=5)
        
        if not sell_signals.empty:
            axes[0].scatter(sell_signals.index, sell_signals['close'], 
                          color='red', marker='v', s=100, label='Sell', zorder=5)
        
        axes[0].set_title(f'{symbol} - Price and Trading Signals')
        axes[0].set_ylabel('Price')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 2. 权益曲线
        axes[1].plot(equity_df.index, equity_df['equity'], 
                    label='Portfolio Value', linewidth=2, color='blue')
        axes[1].axhline(y=self.initial_capital, color='r', linestyle='--', 
                       alpha=0.5, label='Initial Capital')
        axes[1].set_title('Portfolio Equity Curve')
        axes[1].set_ylabel('Value ($)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # 3. RSI指标
        if 'rsi' in signals.columns:
            axes[2].plot(signals.index, signals['rsi'], label='RSI', color='purple')
            axes[2].axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought')
            axes[2].axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold')
            axes[2].set_title('RSI Indicator')
            axes[2].set_ylabel('RSI')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
        else:
            axes[2].plot(signals.index, signals['close'].pct_change().rolling(20).std(), 
                        label='Volatility', color='orange')
            axes[2].set_title('Price Volatility')
            axes[2].set_ylabel('Volatility')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
        
        # 4. 持仓状态
        axes[3].fill_between(equity_df.index, 0, equity_df['position'], 
                           alpha=0.3, label='Position Size', color='lightblue')
        axes[3].set_title('Position Size Over Time')
        axes[3].set_ylabel('Position')
        axes[3].set_xlabel('Time')
        axes[3].legend()
        axes[3].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()

def main():
    """主函数"""
    print("🚀 真实数据回测系统")
    print("=" * 60)
    
    # 配置
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    timeframe = '4h'  # 4小时K线
    days = 60  # 60天历史数据
    
    # 创建回测器
    backtester = RealDataBacktester(initial_capital=10000)
    
    # 创建策略
    strategies = [
        SimpleMovingAverageStrategy(fast_period=12, slow_period=26),
        SimpleTrendStrategy(ma_period=20)
    ]
    
    all_results = {}
    
    # 对每个币种和策略进行回测
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"📊 回测币种: {symbol}")
        
        # 获取历史数据
        data = backtester.fetch_historical_data(symbol, timeframe, days)
        
        if data.empty:
            print(f"跳过 {symbol} - 数据获取失败")
            continue
        
        symbol_results = {}
        
        for strategy in strategies:
            print(f"\n策略: {strategy.name}")
            
            # 运行回测
            result = backtester.run_backtest(data, strategy, symbol)
            
            if result:
                symbol_results[strategy.name] = result
                
                # 输出结果
                print(f"总收益率: {result['total_return']:.2%}")
                print(f"总交易次数: {result['total_trades']}")
                print(f"胜率: {result['win_rate']:.2%}")
                print(f"最大回撤: {result['max_drawdown']:.2%}")
                
                # 保存图表
                safe_symbol = symbol.replace('/', '_')
                save_path = f"results/real_backtest_{safe_symbol}_{strategy.name.lower()}.png"
                os.makedirs("results", exist_ok=True)
                backtester.plot_results(result, save_path)
        
        all_results[symbol] = symbol_results
    
    # 生成汇总报告
    print(f"\n{'='*60}")
    print("📈 回测结果汇总")
    print(f"{'='*60}")
    
    summary_data = []
    for symbol, strategies_results in all_results.items():
        for strategy_name, result in strategies_results.items():
            summary_data.append({
                'Symbol': symbol,
                'Strategy': strategy_name,
                'Return': f"{result['total_return']:.2%}",
                'Trades': result['total_trades'],
                'Win Rate': f"{result['win_rate']:.2%}",
                'Max DD': f"{result['max_drawdown']:.2%}"
            })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        print(summary_df.to_string(index=False))
        
        # 保存汇总结果
        summary_df.to_csv('results/backtest_summary.csv', index=False)
        print(f"\n汇总结果已保存到: results/backtest_summary.csv")
    
    print(f"\n🎯 回测完成！")
    print("所有图表和结果文件保存在 results/ 目录")

if __name__ == "__main__":
    main()
