#!/usr/bin/env python3
"""
测试真实数据集成
验证系统使用真实市场数据的能力
"""

import sys
import os
sys.path.append('.')

from modules.real_data_source import RealDataSource
from strategies.trend_ma_breakout import TrendMABreakoutStrategy
from modules.backtest_module import BacktestModule
import pandas as pd

def test_real_data_integration():
    """测试真实数据集成"""
    print("🚀 测试TradeFan系统真实数据集成")
    print("=" * 60)
    
    # 1. 测试数据源
    print("\n📊 Step 1: 测试数据源连接")
    data_source = RealDataSource()
    
    # 测试多个数据源
    test_symbols = {
        'binance': 'BTCUSDT',
        'yahoo': 'BTC-USD'
    }
    
    successful_sources = []
    
    for source, symbol in test_symbols.items():
        try:
            print(f"   测试 {source}: {symbol}")
            data = data_source.get_data(
                symbol=symbol,
                timeframe='1d',
                start_date='2024-01-01',
                end_date='2024-01-31',
                source=source
            )
            
            if len(data) > 0:
                print(f"   ✅ {source} 成功: {len(data)} 条记录")
                print(f"      价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
                successful_sources.append((source, symbol, data))
            else:
                print(f"   ❌ {source} 失败: 无数据")
                
        except Exception as e:
            print(f"   ❌ {source} 失败: {str(e)}")
    
    if not successful_sources:
        print("❌ 所有数据源都失败，无法继续测试")
        return False
    
    # 2. 测试策略计算
    print(f"\n📈 Step 2: 测试策略计算 (使用{successful_sources[0][0]}数据)")
    source_name, symbol, data = successful_sources[0]
    
    try:
        # 创建策略实例
        strategy = TrendMABreakoutStrategy()
        
        # 准备数据格式
        df = data.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # 计算技术指标
        df_with_indicators = strategy.calculate_indicators(df)
        print(f"   ✅ 技术指标计算成功")
        print(f"      指标数量: {len(df_with_indicators.columns)} 个")
        print(f"      指标列表: {list(df_with_indicators.columns)}")
        
        # 生成交易信号
        signals = strategy.generate_signals(df_with_indicators)
        buy_signals = len(signals[signals['signal'] == 'buy'])
        sell_signals = len(signals[signals['signal'] == 'sell'])
        
        print(f"   ✅ 交易信号生成成功")
        print(f"      买入信号: {buy_signals} 个")
        print(f"      卖出信号: {sell_signals} 个")
        
    except Exception as e:
        print(f"   ❌ 策略计算失败: {str(e)}")
        return False
    
    # 3. 测试回测功能
    print(f"\n🔄 Step 3: 测试回测功能")
    try:
        # 简化的回测配置
        config = {
            'initial_capital': 10000,
            'commission': 0.001,
            'slippage': 0.001
        }
        
        # 创建回测模块
        backtest = BacktestModule(config)
        
        # 执行回测
        result = backtest.run_backtest(
            strategy=strategy,
            data=df_with_indicators,
            symbol=symbol
        )
        
        print(f"   ✅ 回测执行成功")
        print(f"      总收益率: {result['total_return']:.2%}")
        print(f"      最大回撤: {result['max_drawdown']:.2%}")
        print(f"      夏普比率: {result['sharpe_ratio']:.4f}")
        print(f"      交易次数: {result['total_trades']}")
        
    except Exception as e:
        print(f"   ❌ 回测失败: {str(e)}")
        return False
    
    # 4. 数据质量分析
    print(f"\n📋 Step 4: 数据质量分析")
    try:
        print(f"   数据源: {source_name}")
        print(f"   交易对: {symbol}")
        print(f"   数据量: {len(data)} 条记录")
        print(f"   时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
        print(f"   价格统计:")
        print(f"      最高价: ${data['high'].max():.2f}")
        print(f"      最低价: ${data['low'].min():.2f}")
        print(f"      平均价: ${data['close'].mean():.2f}")
        print(f"      价格波动率: {data['close'].pct_change().std():.4f}")
        
        # 检查数据完整性
        missing_data = data.isnull().sum().sum()
        print(f"   数据完整性: {len(data) - missing_data}/{len(data)} ({(1-missing_data/len(data))*100:.1f}%)")
        
    except Exception as e:
        print(f"   ❌ 数据质量分析失败: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎉 真实数据集成测试完成！")
    print("\n✅ 系统现在可以使用真实市场数据进行:")
    print("   • 技术指标计算")
    print("   • 交易信号生成") 
    print("   • 策略回测分析")
    print("   • 数据缓存优化")
    
    print(f"\n📊 推荐下一步:")
    print("   1. 运行完整回测: python3 complete_demo.py")
    print("   2. 测试更多策略: 添加新的策略类")
    print("   3. 优化参数: 使用真实数据进行参数优化")
    print("   4. 实盘准备: 配置交易所API接口")
    
    return True

if __name__ == "__main__":
    test_real_data_integration()
