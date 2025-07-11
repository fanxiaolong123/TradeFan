#!/usr/bin/env python3
"""
短线交易系统测试脚本
Test Script for Scalping Trading System

用于验证系统各个组件的功能
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_scalping_strategy():
    """测试短线策略"""
    print("🧪 测试短线策略...")
    
    try:
        from strategies.scalping_strategy import ScalpingStrategy
        
        # 创建策略实例
        strategy = ScalpingStrategy()
        
        # 生成测试数据
        data = generate_test_data(100)
        
        # 计算指标
        data_with_indicators = strategy.calculate_indicators(data)
        print(f"✅ 指标计算成功，数据形状: {data_with_indicators.shape}")
        
        # 生成信号
        data_with_signals = strategy.generate_signals(data_with_indicators)
        signals = data_with_signals['signal']
        signal_count = len(signals[signals != 0])
        print(f"✅ 信号生成成功，共生成 {signal_count} 个信号")
        
        # 检查必要的列
        required_columns = ['ema_fast', 'ema_medium', 'bb_upper', 'bb_lower', 'rsi', 'macd']
        missing_columns = [col for col in required_columns if col not in data_with_indicators.columns]
        
        if missing_columns:
            print(f"❌ 缺失指标列: {missing_columns}")
        else:
            print("✅ 所有必要指标列都存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 短线策略测试失败: {e}")
        return False

def test_timeframe_analyzer():
    """测试多时间框架分析器"""
    print("\n🧪 测试多时间框架分析器...")
    
    try:
        from modules.timeframe_analyzer import MultiTimeframeAnalyzer
        
        # 创建分析器
        analyzer = MultiTimeframeAnalyzer()
        
        # 生成多时间框架数据
        data_dict = {
            '5m': generate_test_data(200),
            '15m': generate_test_data(100),
            '30m': generate_test_data(50),
            '1h': generate_test_data(25)
        }
        
        # 分析所有时间框架
        analyses = analyzer.analyze_all_timeframes('BTC/USDT', data_dict)
        print(f"✅ 多时间框架分析成功，分析了 {len(analyses)} 个时间框架")
        
        # 测试趋势一致性
        alignment = analyzer.get_trend_alignment(analyses)
        print(f"✅ 趋势一致性分析: 得分 {alignment['alignment_score']:.1f}, 主导趋势 {alignment['dominant_trend']}")
        
        # 测试入场确认
        if analyses:
            confirmation = analyzer.get_entry_confirmation(analyses, '5m')
            print(f"✅ 入场确认: {'通过' if confirmation['confirmed'] else '未通过'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 多时间框架分析器测试失败: {e}")
        return False

def test_realtime_signal_generator():
    """测试实时信号生成器"""
    print("\n🧪 测试实时信号生成器...")
    
    try:
        from modules.realtime_signal_generator import RealTimeSignalGenerator, MarketData
        from strategies.scalping_strategy import ScalpingStrategy
        
        # 创建策略和信号生成器
        strategy = ScalpingStrategy()
        generator = RealTimeSignalGenerator({'scalping': strategy})
        
        # 测试数据缓冲区
        test_data = MarketData(
            symbol='BTC/USDT',
            timestamp=datetime.now(),
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=1000,
            timeframe='5m'
        )
        
        generator.data_buffer.add_data('BTC/USDT', '5m', test_data)
        buffered_data = generator.data_buffer.get_data('BTC/USDT', '5m')
        print(f"✅ 数据缓冲区测试成功，缓存了 {len(buffered_data)} 条数据")
        
        # 测试DataFrame转换
        df = generator.data_buffer.to_dataframe('BTC/USDT', '5m')
        print(f"✅ DataFrame转换成功，形状: {df.shape}")
        
        # 测试性能统计
        stats = generator.get_performance_stats()
        print(f"✅ 性能统计获取成功: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ 实时信号生成器测试失败: {e}")
        return False

def test_configuration():
    """测试配置文件"""
    print("\n🧪 测试配置文件...")
    
    try:
        import yaml
        
        config_path = 'config/scalping_config.yaml'
        if not os.path.exists(config_path):
            print(f"❌ 配置文件不存在: {config_path}")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查必要的配置节
        required_sections = ['trading', 'strategy', 'risk_control', 'signal_generation']
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            print(f"❌ 配置文件缺失节: {missing_sections}")
            return False
        
        print("✅ 配置文件格式正确")
        
        # 检查交易对配置
        symbols = config.get('trading', {}).get('symbols', [])
        enabled_symbols = [s for s in symbols if s.get('enabled', False)]
        print(f"✅ 启用的交易对: {len(enabled_symbols)} 个")
        
        # 检查时间框架配置
        timeframes = config.get('trading', {}).get('timeframes', [])
        enabled_timeframes = [tf for tf in timeframes if tf.get('enabled', False)]
        print(f"✅ 启用的时间框架: {len(enabled_timeframes)} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False

def test_dependencies():
    """测试依赖包"""
    print("\n🧪 测试依赖包...")
    
    dependencies = [
        ('pandas', 'pd'),
        ('numpy', 'np'),
        ('talib', 'talib'),
        ('yaml', 'yaml'),
        ('asyncio', 'asyncio')
    ]
    
    success_count = 0
    
    for dep_name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"✅ {dep_name}")
            success_count += 1
        except ImportError:
            print(f"❌ {dep_name} (未安装)")
    
    print(f"\n依赖包检查: {success_count}/{len(dependencies)} 通过")
    return success_count == len(dependencies)

def test_file_structure():
    """测试文件结构"""
    print("\n🧪 测试文件结构...")
    
    required_files = [
        'strategies/scalping_strategy.py',
        'strategies/base_strategy.py',
        'modules/timeframe_analyzer.py',
        'modules/realtime_signal_generator.py',
        'config/scalping_config.yaml',
        'start_scalping.py',
        'scalping_demo.py'
    ]
    
    required_dirs = [
        'strategies',
        'modules',
        'config',
        'logs',
        'data',
        'results'
    ]
    
    # 检查文件
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    # 检查目录
    missing_dirs = []
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/")
            missing_dirs.append(dir_path)
            # 尝试创建目录
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  → 已创建 {dir_path}/")
            except Exception as e:
                print(f"  → 创建失败: {e}")
    
    return len(missing_files) == 0

def generate_test_data(length: int = 100) -> pd.DataFrame:
    """生成测试数据"""
    np.random.seed(42)  # 固定随机种子
    
    # 生成时间序列
    start_time = datetime.now() - timedelta(minutes=length * 5)
    timestamps = [start_time + timedelta(minutes=i * 5) for i in range(length)]
    
    # 生成价格数据
    base_price = 50000
    prices = []
    current_price = base_price
    
    for i in range(length):
        # 随机游走
        change = np.random.normal(0, 0.01)  # 1%标准差
        current_price *= (1 + change)
        prices.append(current_price)
    
    # 生成OHLCV数据
    data = []
    for i, (timestamp, close) in enumerate(zip(timestamps, prices)):
        open_price = close * (1 + np.random.normal(0, 0.002))
        high_price = max(open_price, close) * (1 + abs(np.random.normal(0, 0.005)))
        low_price = min(open_price, close) * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

async def test_async_functionality():
    """测试异步功能"""
    print("\n🧪 测试异步功能...")
    
    try:
        # 测试异步任务
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "异步任务完成"
        
        result = await dummy_task()
        print(f"✅ {result}")
        
        # 测试并发任务
        tasks = [dummy_task() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        print(f"✅ 并发任务完成: {len(results)} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 异步功能测试失败: {e}")
        return False

def run_performance_test():
    """运行性能测试"""
    print("\n🧪 运行性能测试...")
    
    try:
        from strategies.scalping_strategy import ScalpingStrategy
        import time
        
        strategy = ScalpingStrategy()
        
        # 测试大数据集处理
        large_data = generate_test_data(1000)
        
        start_time = time.time()
        data_with_indicators = strategy.calculate_indicators(large_data)
        indicator_time = time.time() - start_time
        
        start_time = time.time()
        data_with_signals = strategy.generate_signals(data_with_indicators)
        signal_time = time.time() - start_time
        
        print(f"✅ 指标计算时间: {indicator_time:.3f}秒 (1000条数据)")
        print(f"✅ 信号生成时间: {signal_time:.3f}秒 (1000条数据)")
        
        # 性能基准
        if indicator_time < 1.0 and signal_time < 1.0:
            print("✅ 性能测试通过")
            return True
        else:
            print("⚠️  性能可能需要优化")
            return False
            
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 TradeFan 短线交易系统测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("依赖包", test_dependencies()))
    test_results.append(("文件结构", test_file_structure()))
    test_results.append(("配置文件", test_configuration()))
    test_results.append(("短线策略", test_scalping_strategy()))
    test_results.append(("多时间框架分析", test_timeframe_analyzer()))
    test_results.append(("实时信号生成", test_realtime_signal_generator()))
    test_results.append(("异步功能", await test_async_functionality()))
    test_results.append(("性能测试", run_performance_test()))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"总体结果: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！系统准备就绪。")
        print("\n下一步:")
        print("1. 运行回测: python start_scalping.py backtest")
        print("2. 模拟交易: python start_scalping.py live --paper")
        print("3. 查看指南: cat SCALPING_SYSTEM_GUIDE.md")
    else:
        print("⚠️  部分测试失败，请检查相关组件。")
        print("\n故障排除:")
        print("1. 检查依赖安装: pip install -r requirements.txt")
        print("2. 安装TA-Lib: brew install ta-lib (macOS)")
        print("3. 检查文件完整性")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
