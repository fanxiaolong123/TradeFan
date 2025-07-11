"""
系统测试脚本
验证各个模块是否正常工作
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from modules.utils import ConfigLoader, DataProcessor
        from modules.log_module import LogModule
        from modules.strategy_module import TrendFollowingStrategy
        from modules.risk_control_module import RiskControlModule
        from modules.execution_module import ExecutionModule
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_config_loader():
    """测试配置加载"""
    print("测试配置加载...")
    
    try:
        from modules.utils import ConfigLoader
        config_loader = ConfigLoader()
        
        # 测试基本配置获取
        symbols = config_loader.get_symbols()
        initial_capital = config_loader.get('risk_control.initial_capital', 10000)
        
        print(f"✓ 配置加载成功，找到{len(symbols)}个交易对")
        print(f"✓ 初始资金: {initial_capital}")
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

def test_strategy():
    """测试策略模块"""
    print("测试策略模块...")
    
    try:
        from modules.strategy_module import TrendFollowingStrategy
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        np.random.seed(42)
        
        # 生成模拟价格数据
        price = 50000
        prices = [price]
        for _ in range(99):
            change = np.random.normal(0, 0.02)  # 2%波动率
            price = price * (1 + change)
            prices.append(price)
        
        data = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': [np.random.randint(100, 1000) for _ in prices]
        }, index=dates)
        
        # 测试策略
        strategy_params = {
            'fast_ma': 10,
            'slow_ma': 20,
            'adx_period': 14,
            'adx_threshold': 25,
            'donchian_period': 20
        }
        
        strategy = TrendFollowingStrategy(strategy_params)
        
        # 生成信号
        signals = strategy.generate_signals(data)
        indicators = strategy.calculate_indicators(data)
        
        print(f"✓ 策略测试成功，生成{len(signals)}个信号点")
        print(f"✓ 计算了{len(indicators)}个技术指标")
        
        # 测试最新信号
        latest_signal, latest_indicators = strategy.get_latest_signal(data)
        print(f"✓ 最新信号: {latest_signal}")
        
        return True
    except Exception as e:
        print(f"✗ 策略测试失败: {e}")
        return False

def test_risk_control():
    """测试风险控制模块"""
    print("测试风险控制模块...")
    
    try:
        from modules.risk_control_module import RiskControlModule
        
        config = {
            'risk_control': {
                'max_position_size': 0.1,
                'max_total_position': 0.8,
                'max_drawdown': 0.2,
                'stop_loss': 0.02,
                'take_profit': 0.04,
                'initial_capital': 10000
            }
        }
        
        risk_control = RiskControlModule(config)
        
        # 测试仓位限制检查
        passed, reason, adjusted = risk_control.check_position_limit('BTC/USDT', 0.1, 50000)
        print(f"✓ 仓位检查: {passed}, 原因: {reason}")
        
        # 测试回撤检查
        passed, reason = risk_control.check_drawdown_limit()
        print(f"✓ 回撤检查: {passed}, 原因: {reason}")
        
        # 测试仓位计算
        position_size = risk_control.calculate_position_size('BTC/USDT', 0.5, 50000)
        print(f"✓ 建议仓位大小: {position_size:.6f}")
        
        # 测试投资组合状态
        status = risk_control.get_portfolio_status()
        print(f"✓ 投资组合状态获取成功")
        
        return True
    except Exception as e:
        print(f"✗ 风险控制测试失败: {e}")
        return False

def test_execution():
    """测试执行模块"""
    print("测试执行模块...")
    
    try:
        from modules.execution_module import ExecutionModule
        
        config = {
            'backtest': {
                'commission': 0.001
            }
        }
        
        execution = ExecutionModule(config)
        
        # 创建测试数据
        test_data = pd.DataFrame([{'open': 50000}])
        
        # 测试模拟市价单
        order = execution.simulate_market_order('BTC/USDT', 'buy', 0.001, test_data)
        
        if order:
            print(f"✓ 模拟订单执行成功: {order.symbol} {order.side} {order.filled_amount}")
            print(f"✓ 执行价格: {order.filled_price}, 手续费: {order.commission}")
        else:
            print("✗ 模拟订单执行失败")
            return False
        
        # 测试执行统计
        stats = execution.get_execution_statistics()
        print(f"✓ 执行统计获取成功")
        
        return True
    except Exception as e:
        print(f"✗ 执行模块测试失败: {e}")
        return False

def test_data_processor():
    """测试数据处理工具"""
    print("测试数据处理工具...")
    
    try:
        from modules.utils import DataProcessor
        
        # 创建测试收益率数据
        returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.012])
        
        # 测试各种计算
        cumulative_returns = DataProcessor.calculate_cumulative_returns(returns)
        sharpe_ratio = DataProcessor.calculate_sharpe_ratio(returns)
        max_drawdown = DataProcessor.calculate_max_drawdown(cumulative_returns)
        win_rate = DataProcessor.calculate_win_rate(returns)
        
        print(f"✓ 累积收益率计算成功: {cumulative_returns.iloc[-1]:.4f}")
        print(f"✓ 夏普比率: {sharpe_ratio:.4f}")
        print(f"✓ 最大回撤: {max_drawdown:.4f}")
        print(f"✓ 胜率: {win_rate:.2%}")
        
        return True
    except Exception as e:
        print(f"✗ 数据处理测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("自动交易系统 - 模块测试")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config_loader,
        test_data_processor,
        test_strategy,
        test_risk_control,
        test_execution
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ 测试异常: {e}\n")
    
    print("=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常使用。")
    else:
        print("⚠️  部分测试失败，请检查相关模块。")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n下一步:")
        print("1. 配置API密钥 (编辑 .env 文件)")
        print("2. 调整交易参数 (编辑 config/config.yaml)")
        print("3. 运行回测: python main.py --mode backtest")
        print("4. 查看示例: python examples/run_backtest.py")
    else:
        print("\n请先解决测试失败的问题，然后重新运行测试。")
        sys.exit(1)
