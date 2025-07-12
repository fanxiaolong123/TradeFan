#!/usr/bin/env python3
"""
TradeFan 快速策略开发示例
展示如何立即开始策略开发、回测和优化

运行方式:
python3 examples/quick_strategy_development.py
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入TradeFan核心模块
from strategies.base_strategy import BaseStrategy
from modules.backtest_module import BacktestEngine
from modules.professional_backtest_analyzer import BacktestAnalyzer
from indicators_lib import trend, momentum, volatility, volume

print("🚀 TradeFan 快速策略开发示例")
print("=" * 60)

# 1. 创建自定义策略
class QuickTrendStrategy(BaseStrategy):
    """快速趋势跟踪策略示例"""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = "QuickTrendStrategy"
        
        # 策略参数
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        print(f"📊 计算技术指标...")
        
        # 使用indicators_lib计算指标
        df['ema_fast'] = trend.ema(df['close'], self.ema_fast)
        df['ema_slow'] = trend.ema(df['close'], self.ema_slow)
        df['rsi'] = momentum.rsi(df['close'], self.rsi_period)
        
        # 计算MACD
        macd_line, signal_line, histogram = trend.macd(df['close'])
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = histogram
        
        # 计算布林带
        bb_upper, bb_lower = volatility.bollinger_bands(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_lower'] = bb_lower
        df['bb_middle'] = trend.sma(df['close'], 20)
        
        # 计算ATR用于止损
        df['atr'] = volatility.atr(df['high'], df['low'], df['close'], 14)
        
        print(f"   ✅ 计算完成: EMA, RSI, MACD, 布林带, ATR")
        return df
    
    def generate_signals(self, df):
        """生成交易信号"""
        print(f"🎯 生成交易信号...")
        
        signals = []
        
        for i in range(len(df)):
            if i < max(self.ema_slow, self.rsi_period):
                signals.append('HOLD')
                continue
            
            # 获取当前数据
            ema_fast = df['ema_fast'].iloc[i]
            ema_slow = df['ema_slow'].iloc[i]
            rsi = df['rsi'].iloc[i]
            macd = df['macd'].iloc[i]
            macd_signal = df['macd_signal'].iloc[i]
            close = df['close'].iloc[i]
            bb_upper = df['bb_upper'].iloc[i]
            bb_lower = df['bb_lower'].iloc[i]
            
            # 买入信号
            if (ema_fast > ema_slow and  # 快线在慢线上方
                rsi < self.rsi_overbought and  # RSI不超买
                macd > macd_signal and  # MACD金叉
                close > bb_lower):  # 价格在布林带下轨上方
                signals.append('BUY')
            
            # 卖出信号
            elif (ema_fast < ema_slow and  # 快线在慢线下方
                  rsi > self.rsi_oversold and  # RSI不超卖
                  macd < macd_signal and  # MACD死叉
                  close < bb_upper):  # 价格在布林带上轨下方
                signals.append('SELL')
            
            else:
                signals.append('HOLD')
        
        signal_counts = pd.Series(signals).value_counts()
        print(f"   ✅ 信号生成完成: {dict(signal_counts)}")
        
        return signals

# 2. 生成模拟数据
def generate_sample_data(days=365):
    """生成模拟的BTC价格数据"""
    print(f"📊 生成 {days} 天的模拟BTC数据...")
    
    # 设置随机种子以获得可重复的结果
    np.random.seed(42)
    
    # 生成日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='1H')
    
    # 生成价格数据 (模拟BTC价格走势)
    initial_price = 45000
    returns = np.random.normal(0.0001, 0.02, len(dates))  # 小幅上涨趋势 + 波动
    
    # 添加一些趋势性
    trend = np.linspace(0, 0.3, len(dates))  # 30%的整体上涨趋势
    returns += trend / len(dates)
    
    # 计算价格
    prices = [initial_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # 模拟开高低价
        volatility = abs(np.random.normal(0, 0.01))
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        open_price = close * (1 + np.random.normal(0, 0.005))
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    print(f"   ✅ 数据生成完成: {len(df)} 条记录")
    print(f"   📈 价格范围: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
    
    return df

# 3. 运行策略回测
def run_strategy_backtest():
    """运行策略回测"""
    print(f"\n🔬 开始策略回测...")
    
    # 生成测试数据
    df = generate_sample_data(180)  # 6个月数据
    
    # 策略配置
    strategy_config = {
        'ema_fast': 12,
        'ema_slow': 26,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
    
    # 创建策略实例
    strategy = QuickTrendStrategy(strategy_config)
    
    # 计算指标
    df = strategy.calculate_indicators(df)
    
    # 生成信号
    signals = strategy.generate_signals(df)
    df['signal'] = signals
    
    # 简单回测逻辑
    print(f"\n💰 执行回测交易...")
    
    initial_capital = 10000
    capital = initial_capital
    position = 0
    trades = []
    
    for i in range(1, len(df)):
        current_price = df['close'].iloc[i]
        signal = df['signal'].iloc[i]
        prev_signal = df['signal'].iloc[i-1]
        
        # 买入信号
        if signal == 'BUY' and prev_signal != 'BUY' and position == 0:
            position = capital / current_price
            capital = 0
            trades.append({
                'type': 'BUY',
                'price': current_price,
                'quantity': position,
                'timestamp': df['timestamp'].iloc[i]
            })
        
        # 卖出信号
        elif signal == 'SELL' and prev_signal != 'SELL' and position > 0:
            capital = position * current_price
            trades.append({
                'type': 'SELL',
                'price': current_price,
                'quantity': position,
                'timestamp': df['timestamp'].iloc[i]
            })
            position = 0
    
    # 计算最终价值
    final_price = df['close'].iloc[-1]
    final_value = capital + (position * final_price)
    
    # 计算收益率
    total_return = (final_value - initial_capital) / initial_capital
    
    print(f"   ✅ 回测完成!")
    print(f"   💰 初始资金: ${initial_capital:,.2f}")
    print(f"   💰 最终价值: ${final_value:,.2f}")
    print(f"   📈 总收益率: {total_return:.2%}")
    print(f"   📋 交易次数: {len(trades)}")
    
    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'trades': trades,
        'data': df
    }

# 4. 参数优化示例
def optimize_strategy_parameters():
    """优化策略参数"""
    print(f"\n🔧 开始参数优化...")
    
    # 生成测试数据
    df = generate_sample_data(90)  # 3个月数据用于优化
    
    # 参数范围
    ema_fast_range = [8, 10, 12, 15]
    ema_slow_range = [21, 26, 30, 35]
    rsi_period_range = [10, 14, 18, 21]
    
    best_return = -float('inf')
    best_params = None
    results = []
    
    total_combinations = len(ema_fast_range) * len(ema_slow_range) * len(rsi_period_range)
    current_combination = 0
    
    for ema_fast in ema_fast_range:
        for ema_slow in ema_slow_range:
            for rsi_period in rsi_period_range:
                if ema_fast >= ema_slow:  # 跳过无效组合
                    continue
                
                current_combination += 1
                
                # 测试参数组合
                config = {
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi_period': rsi_period,
                    'rsi_oversold': 30,
                    'rsi_overbought': 70
                }
                
                try:
                    # 创建策略并测试
                    strategy = QuickTrendStrategy(config)
                    test_df = df.copy()
                    test_df = strategy.calculate_indicators(test_df)
                    signals = strategy.generate_signals(test_df)
                    
                    # 简单收益计算
                    buy_signals = [i for i, s in enumerate(signals) if s == 'BUY']
                    sell_signals = [i for i, s in enumerate(signals) if s == 'SELL']
                    
                    if len(buy_signals) > 0 and len(sell_signals) > 0:
                        # 计算简单收益
                        returns = []
                        for buy_idx in buy_signals:
                            # 找到下一个卖出信号
                            next_sell = [s for s in sell_signals if s > buy_idx]
                            if next_sell:
                                sell_idx = next_sell[0]
                                buy_price = test_df['close'].iloc[buy_idx]
                                sell_price = test_df['close'].iloc[sell_idx]
                                ret = (sell_price - buy_price) / buy_price
                                returns.append(ret)
                        
                        if returns:
                            avg_return = np.mean(returns)
                            results.append({
                                'ema_fast': ema_fast,
                                'ema_slow': ema_slow,
                                'rsi_period': rsi_period,
                                'avg_return': avg_return,
                                'num_trades': len(returns)
                            })
                            
                            if avg_return > best_return:
                                best_return = avg_return
                                best_params = config
                
                except Exception as e:
                    continue
                
                # 显示进度
                if current_combination % 10 == 0:
                    progress = current_combination / total_combinations * 100
                    print(f"   🔄 优化进度: {progress:.1f}% ({current_combination}/{total_combinations})")
    
    print(f"   ✅ 参数优化完成!")
    print(f"   🏆 最佳参数组合:")
    if best_params:
        for key, value in best_params.items():
            print(f"      {key}: {value}")
        print(f"   📈 最佳平均收益率: {best_return:.2%}")
    
    # 显示前5个最佳结果
    if results:
        results_df = pd.DataFrame(results)
        top_results = results_df.nlargest(5, 'avg_return')
        print(f"\n   🏅 前5个最佳参数组合:")
        for i, row in top_results.iterrows():
            print(f"      #{len(top_results) - list(top_results.index).index(i)}: "
                  f"EMA({row['ema_fast']},{row['ema_slow']}) RSI({row['rsi_period']}) "
                  f"收益率: {row['avg_return']:.2%} 交易次数: {row['num_trades']}")
    
    return best_params, results

# 5. 实时信号生成示例
def generate_realtime_signals():
    """生成实时信号示例"""
    print(f"\n⚡ 实时信号生成示例...")
    
    # 生成最近的数据
    df = generate_sample_data(30)  # 最近30天
    
    # 使用最佳参数
    config = {
        'ema_fast': 12,
        'ema_slow': 26,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
    
    strategy = QuickTrendStrategy(config)
    df = strategy.calculate_indicators(df)
    signals = strategy.generate_signals(df)
    df['signal'] = signals
    
    # 显示最近的信号
    recent_signals = df.tail(10)[['timestamp', 'close', 'ema_fast', 'ema_slow', 'rsi', 'signal']]
    
    print(f"   📊 最近10个时间点的信号:")
    print(f"   {'时间':<20} {'价格':<8} {'EMA快':<8} {'EMA慢':<8} {'RSI':<6} {'信号':<6}")
    print(f"   {'-'*60}")
    
    for _, row in recent_signals.iterrows():
        timestamp = row['timestamp'].strftime('%m-%d %H:%M')
        price = f"{row['close']:.0f}"
        ema_fast = f"{row['ema_fast']:.0f}"
        ema_slow = f"{row['ema_slow']:.0f}"
        rsi = f"{row['rsi']:.1f}"
        signal = row['signal']
        
        # 根据信号添加颜色标记
        signal_mark = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        
        print(f"   {timestamp:<20} {price:<8} {ema_fast:<8} {ema_slow:<8} {rsi:<6} {signal_mark} {signal}")
    
    # 当前信号
    current_signal = df['signal'].iloc[-1]
    current_price = df['close'].iloc[-1]
    
    print(f"\n   🎯 当前信号: {current_signal}")
    print(f"   💰 当前价格: ${current_price:.2f}")
    
    if current_signal == 'BUY':
        print(f"   ✅ 建议: 考虑买入")
    elif current_signal == 'SELL':
        print(f"   ⚠️  建议: 考虑卖出")
    else:
        print(f"   ⏸️  建议: 持有观望")

# 主函数
def main():
    """主函数"""
    try:
        print("🎯 这个示例将展示:")
        print("   • 如何创建自定义策略")
        print("   • 如何使用indicators_lib计算指标")
        print("   • 如何进行策略回测")
        print("   • 如何优化策略参数")
        print("   • 如何生成实时交易信号")
        print()
        
        # 1. 运行策略回测
        backtest_results = run_strategy_backtest()
        
        # 2. 参数优化
        best_params, optimization_results = optimize_strategy_parameters()
        
        # 3. 实时信号生成
        generate_realtime_signals()
        
        print(f"\n🎉 快速策略开发示例完成!")
        print(f"\n📋 下一步建议:")
        print(f"   1. 修改策略逻辑，添加更多指标")
        print(f"   2. 使用真实历史数据进行回测")
        print(f"   3. 运行 'python3 start_scalping.py backtest' 进行完整回测")
        print(f"   4. 运行 'python3 start_scalping.py live --paper' 进行模拟交易")
        print(f"   5. 查看 'STRATEGY_DEVELOPMENT_GUIDE.md' 获取更多指导")
        
    except Exception as e:
        print(f"❌ 示例运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
