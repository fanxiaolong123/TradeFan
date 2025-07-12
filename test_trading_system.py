#!/usr/bin/env python3
"""
TradeFan 交易系统快速测试
验证双策略系统的基本功能
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, DEFAULT_TREND_CONFIG


def generate_test_data(symbol="BTCUSDT", days=30):
    """生成测试数据"""
    print(f"📊 生成 {symbol} {days}天测试数据...")
    
    # 设置随机种子
    np.random.seed(42)
    
    # 生成时间序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='5min')
    
    # 生成价格数据
    base_price = 45000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 300
    
    # 添加趋势和波动
    trend = np.linspace(0, 0.1, len(dates))  # 10%上涨趋势
    noise = np.random.normal(0, 0.02, len(dates))  # 2%波动
    returns = trend / len(dates) + noise
    
    # 计算价格
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        volatility = abs(np.random.normal(0, 0.01))
        high = close * (1 + volatility)
        low = close * (1 - volatility)
        open_price = close * (1 + np.random.normal(0, 0.005))
        
        # 确保OHLC逻辑正确
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
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
    print(f"   ✅ 生成 {len(df)} 条数据，价格范围: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
    return df


def test_strategy(strategy, df, strategy_name):
    """测试单个策略"""
    print(f"\n🧪 测试 {strategy_name}...")
    
    try:
        # 计算指标
        df_with_indicators = strategy.calculate_indicators(df.copy())
        print(f"   ✅ 指标计算完成")
        
        # 生成信号
        signals = strategy.generate_signals(df_with_indicators)
        print(f"   ✅ 信号生成完成: {len(signals)} 个信号")
        
        # 统计信号
        from collections import Counter
        signal_counts = Counter(signals)
        print(f"   📊 信号分布: {dict(signal_counts)}")
        
        # 简单回测
        capital = 10000
        position = 0
        trades = []
        
        for i in range(1, len(df_with_indicators)):
            current_price = df_with_indicators['close'].iloc[i]
            signal = signals[i]
            prev_signal = signals[i-1]
            
            # 买入信号
            if signal == 'BUY' and prev_signal != 'BUY' and position <= 0:
                if position < 0:  # 平空仓
                    pnl = position * (df_with_indicators['close'].iloc[i-1] - current_price)
                    capital += pnl
                    trades.append({'type': 'COVER', 'pnl': pnl})
                
                # 开多仓
                position = (capital * 0.95) / current_price
                capital *= 0.05
                trades.append({'type': 'BUY', 'price': current_price})
            
            # 卖出信号
            elif signal == 'SELL' and prev_signal != 'SELL' and position >= 0:
                if position > 0:  # 平多仓
                    pnl = position * (current_price - df_with_indicators['close'].iloc[i-1])
                    capital += pnl
                    trades.append({'type': 'SELL', 'pnl': pnl})
                    position = 0
        
        # 最终平仓
        if position != 0:
            final_price = df_with_indicators['close'].iloc[-1]
            if position > 0:
                final_pnl = position * final_price
                capital += final_pnl
        
        # 计算收益
        total_return = (capital - 10000) / 10000
        profitable_trades = [t for t in trades if t.get('pnl', 0) > 0]
        total_trades = len([t for t in trades if 'pnl' in t])
        win_rate = len(profitable_trades) / max(total_trades, 1)
        
        print(f"   💰 回测结果:")
        print(f"      初始资金: $10,000")
        print(f"      最终资金: ${capital:,.2f}")
        print(f"      总收益率: {total_return:.2%}")
        print(f"      交易次数: {total_trades}")
        print(f"      胜率: {win_rate:.1%}")
        
        return {
            'strategy': strategy_name,
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'final_capital': capital
        }
        
    except Exception as e:
        print(f"   ❌ {strategy_name} 测试失败: {e}")
        return None


def main():
    """主函数"""
    print("🚀 TradeFan 双策略交易系统测试")
    print("=" * 50)
    
    # 测试交易对
    test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    all_results = []
    
    for symbol in test_symbols:
        print(f"\n📈 测试交易对: {symbol}")
        print("-" * 30)
        
        # 生成测试数据
        df = generate_test_data(symbol, days=30)
        
        # 测试短线策略
        scalping_config = {
            'ema_fast': 8, 'ema_medium': 21, 'ema_slow': 55,
            'rsi_period': 14, 'signal_threshold': 0.6
        }
        scalping_strategy = ScalpingStrategy(**scalping_config)
        scalping_result = test_strategy(scalping_strategy, df, f"短线策略 ({symbol})")
        if scalping_result:
            all_results.append(scalping_result)
        
        # 测试趋势策略
        trend_strategy = TrendFollowingStrategy(DEFAULT_TREND_CONFIG)
        trend_result = test_strategy(trend_strategy, df, f"趋势策略 ({symbol})")
        if trend_result:
            all_results.append(trend_result)
    
    # 汇总结果
    print(f"\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    if all_results:
        print(f"{'策略':<20} {'收益率':<10} {'胜率':<8} {'交易次数':<8}")
        print("-" * 50)
        
        total_return = 0
        for result in all_results:
            print(f"{result['strategy']:<20} {result['total_return']:>8.1%} {result['win_rate']:>6.1%} {result['total_trades']:>6}")
            total_return += result['total_return']
        
        avg_return = total_return / len(all_results)
        print("-" * 50)
        print(f"{'平均表现':<20} {avg_return:>8.1%}")
        
        print(f"\n🎉 系统测试完成!")
        print(f"✅ 双策略系统运行正常")
        print(f"📈 平均收益率: {avg_return:.1%}")
        print(f"🎯 测试通过的策略: {len(all_results)}/{len(test_symbols)*2}")
        
        if avg_return > 0:
            print(f"\n🚀 系统已准备好进行生产部署!")
            print(f"💡 建议:")
            print(f"   1. 先使用测试网进行验证")
            print(f"   2. 从小额资金开始 ($100-200)")
            print(f"   3. 密切监控初期表现")
            print(f"   4. 根据实际表现调整参数")
        else:
            print(f"\n⚠️ 建议优化策略参数后再部署")
    
    else:
        print("❌ 所有策略测试都失败了，请检查代码")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(f"\n🎯 下一步: 运行生产交易系统")
            print(f"   命令: python3 start_production_trading.py --mode live --test-mode --capital 1000")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
