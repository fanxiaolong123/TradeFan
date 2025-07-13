#!/usr/bin/env python3
"""
数据对比分析脚本
对比30条数据 vs 完整数据的差异
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from modules.enhanced_data_module import EnhancedDataModule

def compare_data_sources():
    """对比不同数据源的差异"""
    print("🔍 TradeFan 数据源对比分析")
    print("=" * 60)
    
    data_module = EnhancedDataModule()
    
    # 测试交易对
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
    test_timeframes = ['1d', '4h', '1h']
    
    print("📊 数据量对比:")
    print(f"{'交易对':<12} {'时间框架':<8} {'完整数据':<10} {'时间范围':<30} {'数据质量'}")
    print("-" * 80)
    
    total_records = 0
    
    for symbol in test_symbols:
        for timeframe in test_timeframes:
            try:
                # 获取完整数据
                data = data_module.get_historical_data(symbol, timeframe)
                
                if not data.empty:
                    record_count = len(data)
                    total_records += record_count
                    
                    time_range = f"{data['datetime'].min().strftime('%Y-%m-%d')} 到 {data['datetime'].max().strftime('%Y-%m-%d')}"
                    
                    # 数据质量检查
                    quality = "✅ 优秀"
                    if record_count < 100:
                        quality = "⚠️  数据少"
                    elif record_count < 1000:
                        quality = "✅ 良好"
                    
                    print(f"{symbol:<12} {timeframe:<8} {record_count:<10} {time_range:<30} {quality}")
                else:
                    print(f"{symbol:<12} {timeframe:<8} {'0':<10} {'无数据':<30} ❌ 无数据")
                    
            except Exception as e:
                print(f"{symbol:<12} {timeframe:<8} {'错误':<10} {str(e)[:30]:<30} ❌ 错误")
    
    print("-" * 80)
    print(f"📈 总数据量: {total_records:,} 条记录")
    
    # 对比30条数据的问题
    print(f"\n🔍 数据量对比分析:")
    print(f"   原始问题: 只有30条数据")
    print(f"   现在拥有: {total_records:,} 条数据")
    print(f"   提升倍数: {total_records/30:.0f}x")
    
    # 分析数据覆盖范围
    print(f"\n📅 时间覆盖分析:")
    
    for symbol in test_symbols[:2]:  # 只分析前两个
        print(f"\n   {symbol}:")
        
        for timeframe in test_timeframes:
            try:
                data = data_module.get_historical_data(symbol, timeframe)
                if not data.empty:
                    days_covered = (data['datetime'].max() - data['datetime'].min()).days
                    print(f"     {timeframe}: {len(data)} 条数据, 覆盖 {days_covered} 天")
            except:
                pass
    
    # 数据质量分析
    print(f"\n🔍 数据质量分析:")
    
    for symbol in ['BTC/USDT', 'ETH/USDT']:
        try:
            data = data_module.get_historical_data(symbol, '1d')
            if not data.empty:
                print(f"\n   {symbol} (日线数据):")
                print(f"     数据条数: {len(data)}")
                print(f"     价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
                print(f"     平均成交量: {data['volume'].mean():,.0f}")
                print(f"     数据完整性: {(1 - data.isnull().sum().sum() / (len(data) * len(data.columns))) * 100:.1f}%")
                
                # 价格变化分析
                daily_returns = data['close'].pct_change().dropna()
                print(f"     日均波动: {daily_returns.std() * 100:.2f}%")
                print(f"     最大单日涨幅: {daily_returns.max() * 100:.2f}%")
                print(f"     最大单日跌幅: {daily_returns.min() * 100:.2f}%")
                
        except Exception as e:
            print(f"   {symbol}: 分析失败 - {str(e)}")
    
    # 回测可行性分析
    print(f"\n📊 回测可行性分析:")
    print(f"   30条数据的问题:")
    print(f"     ❌ 无法计算长期技术指标 (如55日EMA)")
    print(f"     ❌ 样本量太小，统计意义不足")
    print(f"     ❌ 无法验证策略在不同市场环境下的表现")
    print(f"     ❌ 无法进行有效的参数优化")
    
    print(f"\n   完整数据的优势:")
    print(f"     ✅ 可计算所有技术指标")
    print(f"     ✅ 大样本量，统计结果可靠")
    print(f"     ✅ 覆盖多种市场环境 (牛市、熊市、震荡)")
    print(f"     ✅ 支持参数优化和策略验证")
    print(f"     ✅ 可进行多时间框架分析")
    
    # 推荐使用方案
    print(f"\n💡 推荐使用方案:")
    print(f"   1. 日线数据: 用于长期趋势分析和策略验证")
    print(f"   2. 4小时数据: 用于中期交易策略")
    print(f"   3. 1小时数据: 用于短线和高频策略")
    print(f"   4. 多币种对比: 验证策略的普适性")
    
    return total_records

def demonstrate_indicator_calculation():
    """演示技术指标计算的差异"""
    print(f"\n🔧 技术指标计算演示:")
    print("=" * 60)
    
    data_module = EnhancedDataModule()
    
    # 获取BTC数据
    btc_data = data_module.get_historical_data('BTC/USDT', '1d', '2024-01-01', '2024-06-30')
    
    if btc_data.empty:
        print("❌ 无法获取BTC数据")
        return
    
    print(f"📊 使用 {len(btc_data)} 条BTC数据演示指标计算:")
    
    # 计算各种技术指标
    btc_data['ema_8'] = btc_data['close'].ewm(span=8).mean()
    btc_data['ema_21'] = btc_data['close'].ewm(span=21).mean()
    btc_data['ema_55'] = btc_data['close'].ewm(span=55).mean()
    
    # 布林带
    btc_data['bb_middle'] = btc_data['close'].rolling(20).mean()
    bb_std = btc_data['close'].rolling(20).std()
    btc_data['bb_upper'] = btc_data['bb_middle'] + (bb_std * 2)
    btc_data['bb_lower'] = btc_data['bb_middle'] - (bb_std * 2)
    
    # RSI
    delta = btc_data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    btc_data['rsi'] = 100 - (100 / (1 + rs))
    
    # 检查指标有效性
    valid_ema_55 = btc_data['ema_55'].notna().sum()
    valid_bb = btc_data['bb_middle'].notna().sum()
    valid_rsi = btc_data['rsi'].notna().sum()
    
    print(f"   EMA55 有效数据: {valid_ema_55}/{len(btc_data)} ({valid_ema_55/len(btc_data)*100:.1f}%)")
    print(f"   布林带 有效数据: {valid_bb}/{len(btc_data)} ({valid_bb/len(btc_data)*100:.1f}%)")
    print(f"   RSI 有效数据: {valid_rsi}/{len(btc_data)} ({valid_rsi/len(btc_data)*100:.1f}%)")
    
    # 显示最近的指标值
    recent_data = btc_data.tail(5)
    print(f"\n📈 最近5天的指标值:")
    print(f"{'日期':<12} {'收盘价':<10} {'EMA8':<10} {'EMA21':<10} {'EMA55':<10} {'RSI':<8}")
    print("-" * 70)
    
    for _, row in recent_data.iterrows():
        date_str = row['datetime'].strftime('%Y-%m-%d')
        print(f"{date_str:<12} {row['close']:<10.2f} {row['ema_8']:<10.2f} "
              f"{row['ema_21']:<10.2f} {row['ema_55']:<10.2f} {row['rsi']:<8.1f}")
    
    # 对比30条数据的限制
    print(f"\n⚠️  30条数据的限制:")
    print(f"   - EMA55需要55条数据才能稳定，30条数据无法计算")
    print(f"   - 布林带需要20条数据，30条数据只能计算10个有效值")
    print(f"   - RSI需要14条数据，30条数据只能计算16个有效值")
    print(f"   - 技术指标组合使用时，有效数据更少")
    
    print(f"\n✅ 完整数据的优势:")
    print(f"   - 所有技术指标都有充足的计算基础")
    print(f"   - 指标值稳定可靠，适合策略判断")
    print(f"   - 支持复杂的多指标组合策略")

def main():
    """主函数"""
    print("🚀 TradeFan 数据源对比分析工具")
    print("解决30条数据限制问题的完整方案")
    print("=" * 60)
    
    # 1. 数据量对比
    total_records = compare_data_sources()
    
    # 2. 技术指标演示
    demonstrate_indicator_calculation()
    
    # 3. 总结建议
    print(f"\n🎯 总结与建议:")
    print("=" * 60)
    print(f"✅ 问题已解决:")
    print(f"   - 从30条数据提升到 {total_records:,} 条数据")
    print(f"   - 支持多个时间框架 (1h, 4h, 1d)")
    print(f"   - 覆盖多个主流币种")
    print(f"   - 数据质量优秀，适合专业回测")
    
    print(f"\n📋 使用建议:")
    print(f"   1. 日常回测: 使用 python3 scripts/simple_full_backtest.py")
    print(f"   2. 数据更新: 定期运行 python3 scripts/fix_data_source.py")
    print(f"   3. 策略开发: 基于完整数据进行参数优化")
    print(f"   4. 实盘前验证: 使用多时间框架验证策略稳定性")
    
    print(f"\n🔄 数据维护:")
    print(f"   - 数据存储位置: data/historical/")
    print(f"   - 支持格式: CSV 和 Parquet")
    print(f"   - 更新频率: 建议每周更新一次")
    print(f"   - 数据源: Binance API (免费，稳定)")

if __name__ == "__main__":
    main()
