"""
基础系统测试脚本
测试不依赖TA-Lib的核心功能
"""

import sys
import os
import pandas as pd
import numpy as np

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试基础模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    
    try:
        import ccxt
        import pandas as pd
        import numpy as np
        import yaml
        from dotenv import load_dotenv
        print("✓ 基础依赖包导入成功")
        
        from modules.utils import ConfigLoader
        from modules.log_module import LogModule
        print("✓ 工具模块导入成功")
        
        from modules.simple_strategy import SimpleMovingAverageStrategy, SimpleTrendStrategy
        print("✓ 简化策略模块导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_config_loader():
    """测试配置加载"""
    print("=" * 50)
    print("测试配置加载...")
    
    try:
        from modules.utils import ConfigLoader
        config_loader = ConfigLoader()
        
        # 测试基本配置获取
        symbols = config_loader.get_symbols()
        initial_capital = config_loader.get('risk_control.initial_capital', 10000)
        
        print(f"✓ 配置加载成功")
        print(f"  - 交易对数量: {len(symbols)}")
        print(f"  - 初始资金: {initial_capital}")
        print(f"  - 交易对列表: {[s['symbol'] for s in symbols]}")
        
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

def test_data_connection():
    """测试数据连接"""
    print("=" * 50)
    print("测试数据连接...")
    
    try:
        import ccxt
        
        # 创建交易所连接（只读模式）
        exchange = ccxt.binance({
            'sandbox': True,  # 使用测试环境
            'enableRateLimit': True,
        })
        
        # 测试获取市场数据
        markets = exchange.load_markets()
        print(f"✓ 成功连接到币安交易所")
        print(f"  - 可用交易对数量: {len(markets)}")
        
        # 测试获取K线数据
        symbol = 'BTC/USDT'
        if symbol in markets:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=10)
            print(f"✓ 成功获取 {symbol} K线数据")
            print(f"  - 数据条数: {len(ohlcv)}")
        
        return True
    except Exception as e:
        print(f"✗ 数据连接失败: {e}")
        print("  提示: 这可能是网络问题，不影响离线功能")
        return False

def test_strategy():
    """测试策略模块"""
    print("=" * 50)
    print("测试策略模块...")
    
    try:
        from modules.simple_strategy import SimpleMovingAverageStrategy, SimpleTrendStrategy
        
        # 生成测试数据
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        prices = 50000 + np.cumsum(np.random.randn(100) * 100)  # BTC价格模拟
        
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(100) * 10,
            'high': prices + np.abs(np.random.randn(100) * 20),
            'low': prices - np.abs(np.random.randn(100) * 20),
            'close': prices,
            'volume': np.random.randint(10, 1000, 100)
        })
        
        # 测试简单移动平均策略
        ma_strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=20)
        ma_result = ma_strategy.generate_signals(test_data)
        
        buy_signals = (ma_result['signal'] == 1).sum()
        sell_signals = (ma_result['signal'] == -1).sum()
        
        print(f"✓ 移动平均策略测试成功")
        print(f"  - 买入信号: {buy_signals}")
        print(f"  - 卖出信号: {sell_signals}")
        
        # 测试趋势策略
        trend_strategy = SimpleTrendStrategy(ma_period=15)
        trend_result = trend_strategy.generate_signals(test_data)
        
        trend_buy = (trend_result['signal'] == 1).sum()
        trend_sell = (trend_result['signal'] == -1).sum()
        
        print(f"✓ 趋势策略测试成功")
        print(f"  - 买入信号: {trend_buy}")
        print(f"  - 卖出信号: {trend_sell}")
        
        return True
    except Exception as e:
        print(f"✗ 策略测试失败: {e}")
        return False

def test_log_module():
    """测试日志模块"""
    print("=" * 50)
    print("测试日志模块...")
    
    try:
        from modules.log_module import LogModule
        from modules.utils import ConfigLoader
        
        config_loader = ConfigLoader()
        logger = LogModule(config_loader.config)
        
        # 测试各种日志记录
        logger.log_system_status("测试", "系统测试开始")
        logger.log_strategy_signal("BTC/USDT", "buy", 50000, {"rsi": 45.5, "ma": 49500})
        logger.log_risk_control("BTC/USDT", "检查通过", "测试风控")
        logger.info("基础日志记录测试")
        
        print("✓ 日志模块测试成功")
        print(f"  - 日志文件路径: logs/")
        
        return True
    except Exception as e:
        print(f"✗ 日志模块测试失败: {e}")
        return False

def test_risk_control():
    """测试风险控制模块"""
    print("=" * 50)
    print("测试风险控制模块...")
    
    try:
        from modules.risk_control_module import RiskControlModule
        from modules.utils import ConfigLoader
        
        config_loader = ConfigLoader()
        risk_control = RiskControlModule(config_loader.config)
        
        # 测试仓位检查
        symbol = "BTC/USDT"
        amount = 0.05  # 5%仓位
        price = 50000
        
        can_trade, reason, adjusted_amount = risk_control.check_position_limit(symbol, amount, price)
        
        print(f"✓ 风险控制模块测试成功")
        print(f"  - 仓位检查: {'通过' if can_trade else '拒绝'}")
        print(f"  - 检查原因: {reason}")
        print(f"  - 调整后金额: {adjusted_amount}")
        
        return True
    except Exception as e:
        print(f"✗ 风险控制测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始系统基础功能测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置加载", test_config_loader),
        ("数据连接", test_data_connection),
        ("策略模块", test_strategy),
        ("日志模块", test_log_module),
        ("风险控制", test_risk_control),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试总结
    print("=" * 50)
    print("📊 测试结果总结")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:12} : {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统基础功能正常")
        return True
    elif passed >= total * 0.7:
        print("⚠️  大部分测试通过，系统基本可用")
        return True
    else:
        print("❌ 多项测试失败，需要修复问题")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n🎯 下一步建议:")
        print("1. 配置API密钥 (编辑 .env 文件)")
        print("2. 运行回测测试: python3 demo.py")
        print("3. 查看结果文件: results/ 目录")
        print("4. 安装TA-Lib以使用完整策略功能")
    else:
        print("\n🔧 需要解决的问题:")
        print("1. 检查依赖包安装")
        print("2. 检查配置文件")
        print("3. 检查网络连接")
    
    sys.exit(0 if success else 1)
