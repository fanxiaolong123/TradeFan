#!/usr/bin/env python3
"""
TradeFan 策略验证脚本
验证策略的基本功能是否正常
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


def create_simple_test_data():
    """创建简单的测试数据"""
    print("📊 创建测试数据...")
    
    # 生成100个数据点
    dates = pd.date_range('2024-01-01', periods=100, freq='5min')
    
    # 生成简单的上涨趋势数据
    base_price = 45000
    prices = []
    for i in range(100):
        # 添加轻微上涨趋势和随机波动
        trend = i * 10  # 每个点上涨10
        noise = np.random.normal(0, 50)  # 50的随机波动
        price = base_price + trend + noise
        prices.append(max(price, 1000))  # 确保价格不会太低
    
    # 创建OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        open_price = close * (1 + np.random.normal(0, 0.001))
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': max(high, open_price, close),
            'low': min(low, open_price, close),
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    print(f"   ✅ 创建了 {len(df)} 条数据")
    print(f"   📈 价格范围: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
    return df


def test_scalping_strategy():
    """测试短线策略"""
    print("\n🧪 测试短线策略...")
    
    try:
        # 创建策略
        config = {
            'ema_fast': 8,
            'ema_medium': 21, 
            'ema_slow': 55,
            'rsi_period': 14,
            'signal_threshold': 0.6
        }
        
        strategy = ScalpingStrategy(**config)
        print(f"   ✅ 策略创建成功: {strategy.name}")
        
        # 获取策略信息
        info = strategy.get_strategy_info()
        print(f"   📋 策略类型: {info.get('type', 'Unknown')}")
        
        # 创建测试数据
        df = create_simple_test_data()
        
        # 计算指标
        df_with_indicators = strategy.calculate_indicators(df)
        print(f"   ✅ 指标计算完成，添加了 {len(df_with_indicators.columns) - len(df.columns)} 个指标")
        
        # 生成信号
        signals = strategy.generate_signals(df_with_indicators)
        print(f"   ✅ 信号生成完成: {len(signals)} 个信号")
        
        # 检查信号类型
        unique_signals = set(signals)
        print(f"   📊 信号类型: {unique_signals}")
        
        if len(unique_signals) > 1:
            from collections import Counter
            signal_counts = Counter(signals)
            print(f"   📈 信号分布: {dict(signal_counts)}")
            return True
        else:
            print(f"   ⚠️ 只生成了一种信号类型，可能需要调整参数")
            return False
            
    except Exception as e:
        print(f"   ❌ 短线策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trend_strategy():
    """测试趋势策略"""
    print("\n🧪 测试趋势跟踪策略...")
    
    try:
        # 创建策略
        strategy = TrendFollowingStrategy(DEFAULT_TREND_CONFIG)
        print(f"   ✅ 策略创建成功: {strategy.name}")
        
        # 获取策略信息
        info = strategy.get_strategy_info()
        print(f"   📋 策略类型: {info.get('type', 'Unknown')}")
        print(f"   📋 核心参数: EMA({info['parameters']['ema_fast']},{info['parameters']['ema_medium']},{info['parameters']['ema_slow']})")
        
        # 创建测试数据
        df = create_simple_test_data()
        
        # 计算指标
        df_with_indicators = strategy.calculate_indicators(df)
        print(f"   ✅ 指标计算完成，添加了 {len(df_with_indicators.columns) - len(df.columns)} 个指标")
        
        # 生成信号
        signals = strategy.generate_signals(df_with_indicators)
        print(f"   ✅ 信号生成完成: {len(signals)} 个信号")
        
        # 检查信号类型
        unique_signals = set(signals)
        print(f"   📊 信号类型: {unique_signals}")
        
        if len(unique_signals) > 1:
            from collections import Counter
            signal_counts = Counter(signals)
            print(f"   📈 信号分布: {dict(signal_counts)}")
            return True
        else:
            print(f"   ⚠️ 只生成了一种信号类型，可能需要调整参数")
            return False
            
    except Exception as e:
        print(f"   ❌ 趋势策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 TradeFan 策略验证测试")
    print("=" * 40)
    
    # 测试短线策略
    scalping_ok = test_scalping_strategy()
    
    # 测试趋势策略
    trend_ok = test_trend_strategy()
    
    # 总结
    print("\n" + "=" * 40)
    print("📊 验证结果总结")
    print("=" * 40)
    
    print(f"短线策略: {'✅ 通过' if scalping_ok else '❌ 失败'}")
    print(f"趋势策略: {'✅ 通过' if trend_ok else '❌ 失败'}")
    
    if scalping_ok and trend_ok:
        print(f"\n🎉 所有策略验证通过！")
        print(f"✅ 系统已准备好进行交易")
        print(f"\n🚀 下一步建议:")
        print(f"   1. 运行更详细的回测")
        print(f"   2. 在测试网上进行小额测试")
        print(f"   3. 监控系统表现")
        return True
    else:
        print(f"\n⚠️ 部分策略验证失败")
        print(f"🔧 建议检查策略代码和参数配置")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n⚠️ 验证被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 验证过程出错: {e}")
        sys.exit(1)
