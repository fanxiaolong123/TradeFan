"""
回测示例脚本
演示如何使用交易系统进行回测
"""

import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import TradingSystem

def run_simple_backtest():
    """运行简单回测示例"""
    print("=" * 60)
    print("自动交易系统回测示例")
    print("=" * 60)
    
    try:
        # 创建交易系统
        trading_system = TradingSystem()
        
        # 设置回测参数
        symbols = ['BTC/USDT', 'ETH/USDT']
        strategy_name = 'TrendFollowing'
        
        print(f"回测币种: {symbols}")
        print(f"使用策略: {strategy_name}")
        print("开始回测...")
        
        # 运行回测
        results = trading_system.run_backtest(symbols, strategy_name)
        
        if results:
            print("\n" + "=" * 60)
            print("回测结果摘要:")
            print("=" * 60)
            print(f"总收益率: {results.get('total_return', 0):.2%}")
            print(f"年化收益率: {results.get('annual_return', 0):.2%}")
            print(f"夏普比率: {results.get('sharpe_ratio', 0):.4f}")
            print(f"最大回撤: {results.get('max_drawdown', 0):.2%}")
            print(f"胜率: {results.get('win_rate', 0):.2%}")
            print(f"总交易次数: {results.get('total_trades', 0)}")
            print(f"盈利交易: {results.get('winning_trades', 0)}")
            print(f"亏损交易: {results.get('losing_trades', 0)}")
            print(f"盈亏比: {results.get('profit_factor', 0):.2f}")
            print("=" * 60)
            
            print("\n回测完成！")
            print("详细结果已保存到 results/ 目录")
            print("图表已保存为 PNG 文件")
        else:
            print("回测失败，请检查配置和日志")
            
    except Exception as e:
        print(f"回测执行失败: {e}")

def run_multi_strategy_comparison():
    """运行多策略对比示例"""
    print("=" * 60)
    print("多策略对比回测示例")
    print("=" * 60)
    
    try:
        # 创建交易系统
        trading_system = TradingSystem()
        
        # 设置对比参数
        symbols = ['BTC/USDT']
        strategies = ['TrendFollowing']  # 可以添加更多策略
        
        print(f"对比币种: {symbols}")
        print(f"对比策略: {strategies}")
        
        # 运行策略对比
        comparison_results = trading_system.backtest_module.compare_strategies(symbols, strategies)
        
        print("\n" + "=" * 60)
        print("策略对比结果:")
        print("=" * 60)
        
        for strategy_name, results in comparison_results.items():
            if results:
                print(f"\n{strategy_name}:")
                print(f"  总收益率: {results.get('total_return', 0):.2%}")
                print(f"  夏普比率: {results.get('sharpe_ratio', 0):.4f}")
                print(f"  最大回撤: {results.get('max_drawdown', 0):.2%}")
                print(f"  胜率: {results.get('win_rate', 0):.2%}")
            else:
                print(f"\n{strategy_name}: 回测失败")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"多策略对比失败: {e}")

if __name__ == "__main__":
    # 运行简单回测
    run_simple_backtest()
    
    print("\n" + "=" * 60)
    
    # 运行多策略对比（可选）
    # run_multi_strategy_comparison()
