#!/usr/bin/env python3
"""
重构后架构演示
展示新的分层目录结构和模块化设计
演示如何使用分离后的各个层级
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分层导入演示
print("🏗️ 展示新的分层架构导入")
print("=" * 50)

# 1. 核心基础设施层 (core/)
print("📦 导入核心基础设施层...")
from core import ConfigManager, LoggerManager, APIClient, TechnicalIndicators

# 2. 策略框架层 (framework/)
print("🎯 导入策略框架层...")
from framework import (
    BaseStrategy, Signal, SignalType, StrategyState,
    StrategyManager, StrategyFactory, StrategyPortfolio,
    PerformanceMetrics
)

# 3. 策略实现层 (strategies/)
print("⚡ 导入策略实现层...")
from strategies.trend import TrendFollowingStrategy
from strategies import STRATEGY_TEMPLATES

print("✅ 所有模块导入成功！")
print()


def generate_sample_data(symbol: str, days: int = 100) -> pd.DataFrame:
    """生成示例市场数据"""
    np.random.seed(42)
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), periods=days*24, freq='H')
    returns = np.random.normal(0, 0.02, len(dates))
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'datetime': dates,
        'open': prices,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates))
    })
    
    return data


async def demo_layered_architecture():
    """演示分层架构的使用"""
    print("🏗️ 分层架构演示")
    print("=" * 50)
    
    # 第1层：核心基础设施
    print("\n📦 第1层：核心基础设施层")
    print("-" * 30)
    
    config_manager = ConfigManager()
    logger_manager = LoggerManager("ArchitectureDemo")
    logger = logger_manager.create_logger("Demo")
    
    print("✅ 配置管理器初始化完成")
    print("✅ 日志管理器初始化完成")
    
    # 第2层：策略框架
    print("\n🎯 第2层：策略框架层")
    print("-" * 30)
    
    strategy_manager = StrategyManager(config_manager, logger_manager)
    
    # 注册策略类
    strategy_manager.register_strategy_class("trend_following", TrendFollowingStrategy)
    
    print("✅ 策略管理器初始化完成")
    print("✅ 策略类注册完成")
    
    # 第3层：策略实现
    print("\n⚡ 第3层：策略实现层")
    print("-" * 30)
    
    # 创建策略实例
    trend_strategy = strategy_manager.create_strategy(
        "trend_following",
        "TrendFollower_Demo",
        STRATEGY_TEMPLATES['trend_following']
    )
    
    strategy_manager.activate_strategy("TrendFollower_Demo")
    
    print("✅ 趋势策略创建并激活")
    
    # 第4层：数据处理（使用核心层的技术指标）
    print("\n📊 数据处理演示")
    print("-" * 30)
    
    # 生成测试数据
    market_data = {
        'BTCUSDT': generate_sample_data('BTCUSDT', 30)
    }
    
    # 使用技术指标计算器
    btc_data = market_data['BTCUSDT']
    btc_with_indicators = TechnicalIndicators.calculate_all_indicators(btc_data)
    
    print(f"✅ 原始数据: {len(btc_data.columns)} 列")
    print(f"✅ 添加指标后: {len(btc_with_indicators.columns)} 列")
    print(f"✅ 新增指标: {len(btc_with_indicators.columns) - len(btc_data.columns)} 个")
    
    # 第5层：信号生成和处理
    print("\n📡 信号生成演示")
    print("-" * 30)
    
    # 处理市场数据生成信号
    all_signals = await strategy_manager.process_market_data(market_data)
    
    for strategy_name, signals in all_signals.items():
        print(f"📈 策略 {strategy_name}:")
        for symbol, signal in signals.items():
            print(f"   {symbol}: {signal.signal_type.name} (强度{signal.strength:.2f}) - {signal.reason}")
    
    # 第6层：性能分析
    print("\n📊 性能分析演示")
    print("-" * 30)
    
    performance_metrics = PerformanceMetrics()
    
    # 获取策略信号历史
    strategy_signals = trend_strategy.metrics.signal_history
    
    if strategy_signals:
        # 计算信号指标
        signal_metrics = performance_metrics.calculate_signal_metrics(strategy_signals)
        
        print("📊 信号性能指标:")
        for name, metric in signal_metrics.items():
            status = "✅" if metric.value >= (metric.benchmark or 0) else "⚠️"
            print(f"   {status} {metric.name}: {metric.value} (基准: {metric.benchmark})")
    
    # 展示架构优势
    print("\n🎉 分层架构优势展示")
    print("=" * 50)
    
    advantages = [
        "📦 核心基础设施层：纯基础功能，无业务逻辑",
        "🎯 策略框架层：统一策略接口，易于扩展",
        "⚡ 策略实现层：按类型分类，便于管理",
        "🔧 模块化设计：各层独立，职责清晰",
        "🚀 易于测试：每层可独立测试",
        "📈 可扩展性：新增功能不影响现有代码"
    ]
    
    for advantage in advantages:
        print(f"   {advantage}")


async def demo_module_independence():
    """演示模块独立性"""
    print("\n🔧 模块独立性演示")
    print("=" * 50)
    
    # 独立使用核心层
    print("\n📦 独立使用核心层:")
    config_manager = ConfigManager()
    logger_manager = LoggerManager("IndependentTest")
    
    # 可以单独使用技术指标
    sample_data = generate_sample_data('TEST', 10)
    indicators = TechnicalIndicators.calculate_all_indicators(sample_data)
    print(f"   ✅ 独立计算技术指标: {len(indicators.columns)} 个指标")
    
    # 独立使用框架层
    print("\n🎯 独立使用框架层:")
    strategy_manager = StrategyManager(config_manager, logger_manager)
    print(f"   ✅ 独立创建策略管理器")
    
    # 独立使用信号系统
    print("\n📡 独立使用信号系统:")
    test_signal = Signal(SignalType.BUY, 0.8, 50000, "测试信号", {'symbol': 'TEST'})
    print(f"   ✅ 独立创建信号: {test_signal}")
    
    # 独立使用性能指标
    print("\n📊 独立使用性能指标:")
    metrics = PerformanceMetrics()
    test_returns = [0.01, -0.005, 0.02, -0.01, 0.015]
    return_metrics = metrics.calculate_return_metrics(test_returns)
    print(f"   ✅ 独立计算性能指标: {len(return_metrics)} 个指标")


async def demo_easy_extension():
    """演示扩展的便利性"""
    print("\n🚀 扩展便利性演示")
    print("=" * 50)
    
    # 演示如何轻松添加新策略
    print("\n⚡ 添加新策略演示:")
    
    class SimpleMAStrategy(BaseStrategy):
        """简单移动平均策略示例"""
        
        async def calculate_indicators(self, data, symbol):
            result = TechnicalIndicators.calculate_all_indicators(data)
            return result
        
        async def generate_signal(self, data, symbol):
            if len(data) < 2:
                return Signal(SignalType.HOLD, 0, data['close'].iloc[-1], "数据不足", {'symbol': symbol})
            
            latest = data.iloc[-1]
            if latest['sma_20'] > latest['sma_50']:
                return Signal(SignalType.BUY, 0.6, latest['close'], "MA金叉", {'symbol': symbol})
            elif latest['sma_20'] < latest['sma_50']:
                return Signal(SignalType.SELL, 0.6, latest['close'], "MA死叉", {'symbol': symbol})
            else:
                return Signal(SignalType.HOLD, 0.1, latest['close'], "MA平行", {'symbol': symbol})
    
    # 注册新策略
    config_manager = ConfigManager()
    logger_manager = LoggerManager("ExtensionDemo")
    strategy_manager = StrategyManager(config_manager, logger_manager)
    
    strategy_manager.register_strategy_class("simple_ma", SimpleMAStrategy)
    
    # 创建新策略实例
    ma_strategy = strategy_manager.create_strategy(
        "simple_ma",
        "SimpleMA_Demo",
        {'parameters': {}, 'timeframes': ['1h']}
    )
    
    print("   ✅ 新策略类定义完成（仅需实现2个方法）")
    print("   ✅ 新策略注册完成")
    print("   ✅ 新策略实例创建完成")
    print("   💡 总代码量：约20行（vs 原来的200+行）")


async def main():
    """主演示函数"""
    print("🏗️ TradeFan 架构重构演示")
    print("展示新的分层目录结构和模块化设计")
    print("=" * 60)
    
    try:
        # 演示分层架构
        await demo_layered_architecture()
        
        # 演示模块独立性
        await demo_module_independence()
        
        # 演示扩展便利性
        await demo_easy_extension()
        
        print("\n" + "=" * 60)
        print("🎉 架构重构演示完成！")
        print("=" * 60)
        
        print("\n💡 重构成果总结:")
        print("   ✅ 清晰的分层架构 - 职责明确，易于理解")
        print("   ✅ 模块化设计 - 各层独立，便于测试")
        print("   ✅ 高度可扩展 - 新增功能简单快速")
        print("   ✅ 代码复用 - 减少重复，提高效率")
        print("   ✅ 易于维护 - 修改影响范围小")
        
        print("\n🎯 目录结构优势:")
        print("   📦 core/ - 纯基础设施，稳定可靠")
        print("   🎯 framework/ - 策略框架，统一接口")
        print("   ⚡ strategies/ - 策略实现，分类管理")
        print("   📊 data/ - 数据处理，独立模块")
        print("   🖥️ monitoring/ - 监控分析，专业工具")
        
        print("\n🚀 下一步计划:")
        print("   1. 完善strategies/目录下的策略实现")
        print("   2. 构建data/层的数据处理系统")
        print("   3. 开发monitoring/层的监控界面")
        print("   4. 实现deployment/层的部署自动化")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
