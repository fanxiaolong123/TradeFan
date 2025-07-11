"""
TradeFan 完整功能演示
展示升级后的量化交易系统的所有核心功能
"""

import os
import sys
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies import list_strategies, get_strategy
from multi_strategy_evaluator import MultiStrategyEvaluator
from parameter_optimizer import ParameterOptimizer
from backtest_visualizer import BacktestVisualizer

def print_header(title: str):
    """打印标题"""
    print("\n" + "="*80)
    print(f"🚀 {title}")
    print("="*80)

def print_section(title: str):
    """打印章节"""
    print(f"\n📊 {title}")
    print("-"*60)

def demo_strategy_system():
    """演示策略系统"""
    print_section("策略插件化系统演示")
    
    # 列出所有可用策略
    strategies = list_strategies()
    print(f"可用策略数量: {len(strategies)}")
    print(f"策略列表: {strategies}")
    
    # 演示策略创建和信息获取
    for strategy_name in strategies:
        try:
            strategy = get_strategy(strategy_name)
            info = strategy.get_strategy_info()
            print(f"\n✅ {strategy_name}:")
            print(f"   描述: {info.get('description', '无描述')}")
            print(f"   默认参数: {info.get('params', {})}")
            
            # 获取参数优化范围
            param_ranges = strategy.get_param_ranges()
            if param_ranges:
                print(f"   可优化参数: {list(param_ranges.keys())}")
        except Exception as e:
            print(f"❌ {strategy_name}: 创建失败 - {e}")

def demo_multi_strategy_evaluation():
    """演示多策略评估"""
    print_section("多策略评估系统演示")
    
    # 创建评估器
    evaluator = MultiStrategyEvaluator()
    
    # 配置测试参数
    strategies = ['trend_ma_breakout', 'donchian_rsi_adx']
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    print(f"测试策略: {strategies}")
    print(f"测试币种: {symbols}")
    
    # 运行多策略回测
    results = evaluator.run_multi_backtest(
        strategies=strategies,
        symbols=symbols,
        timeframe='1h',
        initial_capital=10000,
        parallel=False  # 演示时使用串行避免过多输出
    )
    
    if results:
        print(f"\n✅ 回测完成，共 {len(results)} 个结果")
        
        # 生成对比报告
        report_df = evaluator.generate_comparison_report()
        
        if not report_df.empty:
            print("\n📈 策略对比报告预览:")
            print(report_df.head())
        
        # 获取最佳策略
        best_strategies = evaluator.get_best_strategies(top_n=3)
        print(f"\n🏆 最佳策略组合 (Top 3):")
        for i, item in enumerate(best_strategies, 1):
            result = item['result']
            print(f"{i}. {item['key']}")
            print(f"   综合评分: {item['score']:.3f}")
            print(f"   收益率: {result.get('total_return', 0):.2%}")
            print(f"   夏普比率: {result.get('sharpe_ratio', 0):.3f}")
    else:
        print("❌ 没有成功的回测结果")

def demo_parameter_optimization():
    """演示参数优化"""
    print_section("参数优化系统演示")
    
    # 创建优化器
    optimizer = ParameterOptimizer()
    
    # 定义参数范围 (小范围用于演示)
    param_ranges = {
        'fast_ma': [15, 20, 25],
        'slow_ma': [40, 50, 60],
        'rsi_period': [12, 14, 16]
    }
    
    print("参数优化范围:")
    for param, values in param_ranges.items():
        print(f"  {param}: {values}")
    
    # 执行网格搜索优化
    print("\n🔍 执行网格搜索优化...")
    result = optimizer.grid_search_optimization(
        strategy_name='trend_ma_breakout',
        symbol='BTC/USDT',
        param_ranges=param_ranges,
        objective='sharpe_ratio',
        max_combinations=20,
        parallel=False
    )
    
    if result and 'best_params' in result:
        print(f"\n✅ 优化完成")
        print(f"最佳参数: {result['best_params']}")
        print(f"最佳得分: {result['best_score']:.4f}")
        
        # 保存优化结果
        os.makedirs('results', exist_ok=True)
        optimizer.save_optimization_results('results/demo_optimization.json')
    else:
        print("❌ 参数优化失败")

def demo_visualization():
    """演示可视化功能"""
    print_section("回测可视化演示")
    
    # 创建一个简单的回测结果用于演示
    print("生成演示数据...")
    
    try:
        # 使用评估器生成一个回测结果
        evaluator = MultiStrategyEvaluator()
        
        # 执行单个回测
        result = evaluator._single_backtest(
            'trend_ma_breakout', 'BTC/USDT', '1h', 
            None, None, 10000
        )
        
        if result:
            print("✅ 演示数据生成成功")
            
            # 创建可视化器
            visualizer = BacktestVisualizer()
            
            # 生成综合报告
            report_path = 'results/demo_backtest_report.png'
            os.makedirs('results', exist_ok=True)
            
            print(f"生成可视化报告: {report_path}")
            visualizer.create_comprehensive_report(result, report_path)
            
            print("✅ 可视化演示完成")
        else:
            print("❌ 演示数据生成失败")
            
    except Exception as e:
        print(f"❌ 可视化演示失败: {e}")

def demo_complete_workflow():
    """演示完整工作流程"""
    print_section("完整工作流程演示")
    
    print("🔄 完整量化交易系统工作流程:")
    print("1. 策略开发 → 2. 参数优化 → 3. 多策略对比 → 4. 结果可视化")
    
    try:
        # 1. 创建策略
        print("\n1️⃣ 创建策略实例...")
        strategy = get_strategy('trend_ma_breakout', fast_ma=20, slow_ma=50)
        print(f"✅ 策略创建成功: {strategy.name}")
        
        # 2. 快速参数测试
        print("\n2️⃣ 快速参数测试...")
        optimizer = ParameterOptimizer()
        
        # 小范围参数测试
        quick_params = {
            'fast_ma': [15, 20],
            'slow_ma': [45, 50]
        }
        
        opt_result = optimizer.grid_search_optimization(
            'trend_ma_breakout', 'BTC/USDT', quick_params,
            max_combinations=4, parallel=False
        )
        
        if opt_result and 'best_params' in opt_result:
            print(f"✅ 最优参数: {opt_result['best_params']}")
        
        # 3. 策略对比
        print("\n3️⃣ 策略性能对比...")
        evaluator = MultiStrategyEvaluator()
        
        comparison_results = evaluator.run_multi_backtest(
            strategies=['trend_ma_breakout'],
            symbols=['BTC/USDT'],
            parallel=False
        )
        
        if comparison_results:
            print("✅ 策略对比完成")
        
        # 4. 生成报告
        print("\n4️⃣ 生成最终报告...")
        
        if comparison_results:
            report_df = evaluator.generate_comparison_report()
            print("✅ 报告生成完成")
        
        print("\n🎉 完整工作流程演示成功！")
        
    except Exception as e:
        print(f"❌ 工作流程演示失败: {e}")

def show_project_status():
    """显示项目状态"""
    print_section("项目升级状态")
    
    features = [
        ("✅ 策略插件化系统", "支持多策略独立开发和管理"),
        ("✅ 多策略评估系统", "支持批量回测和性能对比"),
        ("✅ 参数自动优化", "网格搜索和贝叶斯优化"),
        ("✅ 回测可视化分析", "详细图表和性能报告"),
        ("✅ 完整工作流程", "从策略开发到结果分析"),
        ("🟨 实盘交易接口", "基础框架完成，需要API配置"),
        ("🟨 Web监控界面", "规划中，可后续开发"),
        ("🟨 机器学习集成", "框架支持，可扩展AI策略")
    ]
    
    print("项目功能完成度:")
    for status, description in features:
        print(f"{status} {description}")
    
    print(f"\n📁 项目结构:")
    structure = [
        "strategies/          # 策略插件目录",
        "├── base_strategy.py # 策略基类",
        "├── trend_ma_breakout.py # MA趋势策略",
        "├── donchian_rsi_adx.py  # 唐奇安+RSI+ADX策略",
        "└── reversal_bollinger.py # 布林带反转策略",
        "",
        "multi_strategy_evaluator.py # 多策略评估器",
        "parameter_optimizer.py     # 参数优化器",
        "backtest_visualizer.py     # 可视化分析器",
        "complete_demo.py           # 完整功能演示"
    ]
    
    for line in structure:
        print(line)

def main():
    """主演示函数"""
    print_header("TradeFan 量化交易系统 - 完整功能演示")
    
    print("🎯 本演示将展示升级后系统的所有核心功能:")
    print("• 策略插件化管理")
    print("• 多策略批量评估")
    print("• 参数自动优化")
    print("• 回测结果可视化")
    print("• 完整工作流程")
    
    # 显示项目状态
    show_project_status()
    
    # 演示各个功能模块
    try:
        demo_strategy_system()
        demo_multi_strategy_evaluation()
        demo_parameter_optimization()
        demo_visualization()
        demo_complete_workflow()
        
        print_header("演示完成")
        print("🎉 恭喜！TradeFan 量化交易系统升级成功！")
        print("\n📋 下一步建议:")
        print("1. 安装 TA-Lib: ./install_talib.sh")
        print("2. 配置 API 密钥: 编辑 .env 文件")
        print("3. 运行完整测试: python3 test_system.py")
        print("4. 开始策略开发和优化")
        print("5. 准备实盘测试")
        
        print(f"\n📊 生成的文件:")
        print("• results/demo_backtest_report.png - 回测可视化报告")
        print("• results/strategy_comparison_*.csv - 策略对比报告")
        print("• results/demo_optimization.json - 参数优化结果")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        print("请检查依赖安装和配置")

if __name__ == "__main__":
    main()
