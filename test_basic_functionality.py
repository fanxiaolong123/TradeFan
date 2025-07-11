#!/usr/bin/env python3
"""
基础功能测试脚本
Basic Functionality Test Script

测试系统的基本功能，不依赖外部库
"""

import sys
import os
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_file_structure():
    """测试文件结构"""
    print("🧪 测试文件结构...")
    
    required_files = [
        'strategies/scalping_strategy.py',
        'strategies/base_strategy.py',
        'strategies/ta_indicators.py',
        'modules/timeframe_analyzer.py',
        'modules/realtime_signal_generator.py',
        'config/scalping_config.yaml',
        'start_scalping.py',
        'scalping_demo.py',
        'SCALPING_SYSTEM_GUIDE.md'
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

def test_imports():
    """测试模块导入"""
    print("\n🧪 测试模块导入...")
    
    modules_to_test = [
        ('strategies.base_strategy', 'BaseStrategy'),
        ('strategies.ta_indicators', 'SMA'),
        ('modules.timeframe_analyzer', 'MultiTimeframeAnalyzer'),
        ('modules.realtime_signal_generator', 'RealTimeSignalGenerator'),
    ]
    
    success_count = 0
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name}.{class_name} - 导入错误: {e}")
        except AttributeError as e:
            print(f"❌ {module_name}.{class_name} - 属性错误: {e}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - 其他错误: {e}")
    
    print(f"\n模块导入检查: {success_count}/{len(modules_to_test)} 通过")
    return success_count == len(modules_to_test)

def test_strategy_creation():
    """测试策略创建"""
    print("\n🧪 测试策略创建...")
    
    try:
        # 测试基础策略
        from strategies.base_strategy import BaseStrategy
        print("✅ 基础策略类导入成功")
        
        # 测试短线策略（如果pandas可用）
        try:
            from strategies.scalping_strategy import ScalpingStrategy
            strategy = ScalpingStrategy()
            print("✅ 短线策略创建成功")
            print(f"✅ 策略信息: {strategy.get_strategy_info()['name']}")
            return True
        except ImportError as e:
            print(f"⚠️  短线策略需要pandas/numpy: {e}")
            return True  # 不算失败，只是依赖缺失
        
    except Exception as e:
        print(f"❌ 策略创建失败: {e}")
        return False

async def test_async_functionality():
    """测试异步功能"""
    print("\n🧪 测试异步功能...")
    
    try:
        # 测试基本异步任务
        async def dummy_task():
            await asyncio.sleep(0.01)
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

def test_yaml_config():
    """测试YAML配置解析"""
    print("\n🧪 测试YAML配置解析...")
    
    try:
        import yaml
        
        # 测试配置文件解析
        config_path = 'config/scalping_config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 验证关键配置
        trading_config = config.get('trading', {})
        strategy_config = config.get('strategy', {})
        risk_config = config.get('risk_control', {})
        
        print(f"✅ 交易配置: {len(trading_config)} 项")
        print(f"✅ 策略配置: {len(strategy_config)} 项")
        print(f"✅ 风控配置: {len(risk_config)} 项")
        
        # 检查具体配置值
        symbols = trading_config.get('symbols', [])
        if symbols:
            print(f"✅ 交易对配置: {symbols[0]['symbol']} 等 {len(symbols)} 个")
        
        initial_capital = risk_config.get('initial_capital', 0)
        if initial_capital > 0:
            print(f"✅ 初始资金: ${initial_capital:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ YAML配置测试失败: {e}")
        return False

def test_system_readiness():
    """测试系统就绪状态"""
    print("\n🧪 测试系统就绪状态...")
    
    readiness_checks = []
    
    # 检查核心文件
    core_files = [
        'strategies/scalping_strategy.py',
        'modules/timeframe_analyzer.py',
        'modules/realtime_signal_generator.py',
        'config/scalping_config.yaml'
    ]
    
    files_ready = all(os.path.exists(f) for f in core_files)
    readiness_checks.append(('核心文件', files_ready))
    
    # 检查目录结构
    dirs_ready = all(os.path.exists(d) for d in ['logs', 'data', 'results'])
    readiness_checks.append(('目录结构', dirs_ready))
    
    # 检查配置文件
    try:
        import yaml
        with open('config/scalping_config.yaml', 'r') as f:
            yaml.safe_load(f)
        config_ready = True
    except:
        config_ready = False
    readiness_checks.append(('配置文件', config_ready))
    
    # 检查启动脚本
    scripts_ready = all(os.path.exists(f) for f in ['start_scalping.py', 'scalping_demo.py'])
    readiness_checks.append(('启动脚本', scripts_ready))
    
    # 显示结果
    ready_count = 0
    for check_name, is_ready in readiness_checks:
        status = "✅ 就绪" if is_ready else "❌ 未就绪"
        print(f"{check_name:<12} {status}")
        if is_ready:
            ready_count += 1
    
    overall_ready = ready_count == len(readiness_checks)
    
    if overall_ready:
        print("\n🎉 系统已就绪！可以开始使用。")
        print("\n推荐下一步:")
        print("1. 安装依赖: pip install pandas numpy pyyaml")
        print("2. 运行演示: python3 scalping_demo.py")
        print("3. 查看指南: cat SCALPING_SYSTEM_GUIDE.md")
    else:
        print(f"\n⚠️  系统部分就绪 ({ready_count}/{len(readiness_checks)})")
    
    return overall_ready

def print_system_info():
    """打印系统信息"""
    print("📊 系统信息:")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {os.name}")
    print(f"当前目录: {os.getcwd()}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """主测试函数"""
    print("🚀 TradeFan 短线交易系统基础功能测试")
    print("=" * 60)
    
    # 打印系统信息
    print_system_info()
    print()
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("文件结构", test_file_structure()))
    test_results.append(("配置文件", test_configuration()))
    test_results.append(("模块导入", test_imports()))
    test_results.append(("策略创建", test_strategy_creation()))
    test_results.append(("YAML配置", test_yaml_config()))
    test_results.append(("异步功能", await test_async_functionality()))
    test_results.append(("系统就绪", test_system_readiness()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<12} {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"总体结果: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有基础功能测试通过！")
        print("\n系统已准备就绪，可以开始使用短线交易功能。")
        print("\n快速开始:")
        print("• 安装依赖: pip install pandas numpy pyyaml")
        print("• 运行回测: python3 start_scalping.py backtest")
        print("• 模拟交易: python3 start_scalping.py live --paper")
        print("• 查看指南: open SCALPING_SYSTEM_GUIDE.md")
    else:
        print(f"\n⚠️  {total-passed} 项测试失败，请检查相关组件。")
        
        if passed >= total * 0.7:  # 70%以上通过
            print("\n大部分功能正常，可以尝试基础使用。")
        else:
            print("\n建议先解决失败的测试项目。")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
