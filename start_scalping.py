#!/usr/bin/env python3
"""
短线交易系统快速启动脚本
Quick Start Script for Scalping Trading System

提供简单的命令行界面来启动和管理短线交易系统
"""

import argparse
import asyncio
import sys
import os
import yaml
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_config(config_path: str = "config/scalping_config.yaml") -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"配置文件未找到: {config_path}")
        return {}
    except yaml.YAMLError as e:
        print(f"配置文件格式错误: {e}")
        return {}

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    TradeFan 短线交易系统                      ║
║                  Professional Scalping System                ║
╠══════════════════════════════════════════════════════════════╣
║  版本: v2.0.0                                               ║
║  作者: TradeFan Team                                        ║
║  时间: {}                                    ║
╚══════════════════════════════════════════════════════════════╝
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(banner)

def print_system_info(config: dict):
    """打印系统信息"""
    print("系统配置信息:")
    print("=" * 50)
    
    # 交易对信息
    enabled_symbols = [s['symbol'] for s in config.get('trading', {}).get('symbols', []) if s.get('enabled', False)]
    print(f"交易对: {', '.join(enabled_symbols)}")
    
    # 时间框架信息
    enabled_timeframes = [tf['timeframe'] for tf in config.get('trading', {}).get('timeframes', []) if tf.get('enabled', False)]
    print(f"时间框架: {', '.join(enabled_timeframes)}")
    
    # 风险控制信息
    risk_config = config.get('risk_control', {})
    print(f"初始资金: ${risk_config.get('initial_capital', 10000):,}")
    print(f"最大持仓: {risk_config.get('max_positions', 3)}")
    print(f"单笔风险: {risk_config.get('max_total_risk', 0.05)*100:.1f}%")
    
    # 策略信息
    strategy_config = config.get('strategy', {}).get('scalping', {})
    print(f"策略参数: EMA({strategy_config.get('ema_fast', 8)},{strategy_config.get('ema_medium', 21)},{strategy_config.get('ema_slow', 55)})")
    
    print("=" * 50)

async def run_live_trading(config: dict):
    """运行实盘交易"""
    from scalping_demo import ScalpingTradingSystem
    
    print("启动实盘交易模式...")
    print("⚠️  警告: 这是实盘交易，请确保您已经充分测试策略！")
    
    # 确认提示
    if not config.get('development', {}).get('paper_trading', True):
        confirm = input("确认启动实盘交易? (输入 'YES' 确认): ")
        if confirm != 'YES':
            print("已取消实盘交易")
            return
    
    # 创建交易系统
    trading_system = ScalpingTradingSystem()
    
    # 应用配置
    trading_system.config.update({
        'symbols': [s['symbol'] for s in config.get('trading', {}).get('symbols', []) if s.get('enabled', False)],
        'timeframes': [tf['timeframe'] for tf in config.get('trading', {}).get('timeframes', []) if tf.get('enabled', False)],
        'initial_capital': config.get('risk_control', {}).get('initial_capital', 10000),
        'max_positions': config.get('risk_control', {}).get('max_positions', 3),
        'risk_per_trade': config.get('risk_control', {}).get('max_total_risk', 0.05)
    })
    
    try:
        await trading_system.start_trading()
    except KeyboardInterrupt:
        print("\n用户中断交易")
    except Exception as e:
        print(f"交易系统异常: {e}")
    finally:
        await trading_system.shutdown()

async def run_backtest(config: dict, start_date: str = None, end_date: str = None):
    """运行回测"""
    print("启动回测模式...")
    
    # 导入回测模块
    try:
        from modules.backtest_module import BacktestModule
        from strategies.scalping_strategy import ScalpingStrategy
    except ImportError as e:
        print(f"导入回测模块失败: {e}")
        return
    
    # 创建策略
    strategy_config = config.get('strategy', {}).get('scalping', {})
    strategy = ScalpingStrategy(**strategy_config)
    
    # 创建回测模块
    backtest_config = config.get('backtest', {})
    backtest = BacktestModule(
        initial_capital=backtest_config.get('initial_capital', 10000),
        maker_fee=backtest_config.get('maker_fee', 0.001),
        taker_fee=backtest_config.get('taker_fee', 0.001)
    )
    
    # 设置回测参数
    symbols = [s['symbol'] for s in config.get('trading', {}).get('symbols', []) if s.get('enabled', False)]
    timeframes = [tf['timeframe'] for tf in config.get('trading', {}).get('timeframes', []) if tf.get('enabled', False)]
    
    start_date = start_date or backtest_config.get('start_date', '2024-01-01')
    end_date = end_date or backtest_config.get('end_date', '2024-12-31')
    
    print(f"回测期间: {start_date} 到 {end_date}")
    print(f"交易对: {', '.join(symbols)}")
    print(f"时间框架: {', '.join(timeframes)}")
    
    # 运行回测
    try:
        results = await backtest.run_backtest(
            strategy=strategy,
            symbols=symbols,
            timeframes=timeframes,
            start_date=start_date,
            end_date=end_date
        )
        
        # 显示结果
        print("\n回测结果:")
        print("=" * 50)
        for key, value in results.items():
            if isinstance(value, float):
                if 'ratio' in key.lower() or 'rate' in key.lower():
                    print(f"{key}: {value:.2%}")
                else:
                    print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        
    except Exception as e:
        print(f"回测异常: {e}")

def run_optimization(config: dict):
    """运行参数优化"""
    print("启动参数优化...")
    
    opt_config = config.get('optimization', {})
    if not opt_config.get('enabled', False):
        print("参数优化未启用，请在配置文件中启用")
        return
    
    try:
        from modules.optimization_module import OptimizationModule
        from strategies.scalping_strategy import ScalpingStrategy
        
        # 创建优化模块
        optimizer = OptimizationModule()
        
        # 设置优化参数
        param_ranges = opt_config.get('parameter_ranges', {})
        objective = opt_config.get('objective', 'sharpe_ratio')
        method = opt_config.get('method', 'grid_search')
        
        print(f"优化方法: {method}")
        print(f"优化目标: {objective}")
        print(f"参数范围: {param_ranges}")
        
        # 运行优化
        best_params = optimizer.optimize(
            strategy_class=ScalpingStrategy,
            param_ranges=param_ranges,
            objective=objective,
            method=method
        )
        
        print("\n最优参数:")
        print("=" * 30)
        for param, value in best_params.items():
            print(f"{param}: {value}")
            
    except ImportError as e:
        print(f"导入优化模块失败: {e}")
    except Exception as e:
        print(f"优化异常: {e}")

def show_status():
    """显示系统状态"""
    print("系统状态检查...")
    
    # 检查依赖
    dependencies = [
        'pandas', 'numpy', 'talib', 'asyncio', 'websockets', 'yaml'
    ]
    
    print("\n依赖检查:")
    print("-" * 30)
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep}")
        except ImportError:
            print(f"✗ {dep} (未安装)")
    
    # 检查文件
    required_files = [
        'strategies/scalping_strategy.py',
        'modules/timeframe_analyzer.py',
        'modules/realtime_signal_generator.py',
        'config/scalping_config.yaml'
    ]
    
    print("\n文件检查:")
    print("-" * 30)
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (缺失)")
    
    # 检查目录
    required_dirs = ['logs', 'data', 'results']
    
    print("\n目录检查:")
    print("-" * 30)
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ (缺失)")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  → 已创建 {dir_path}/")
            except Exception as e:
                print(f"  → 创建失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TradeFan 短线交易系统')
    
    parser.add_argument('mode', choices=['live', 'backtest', 'optimize', 'status'], 
                       help='运行模式')
    parser.add_argument('--config', '-c', default='config/scalping_config.yaml',
                       help='配置文件路径')
    parser.add_argument('--start-date', help='回测开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='回测结束日期 (YYYY-MM-DD)')
    parser.add_argument('--symbols', nargs='+', help='指定交易对')
    parser.add_argument('--timeframes', nargs='+', help='指定时间框架')
    parser.add_argument('--paper', action='store_true', help='模拟交易模式')
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    
    # 状态检查模式
    if args.mode == 'status':
        show_status()
        return
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print("无法加载配置文件，退出")
        return
    
    # 打印系统信息
    print_system_info(config)
    
    # 应用命令行参数
    if args.symbols:
        # 更新交易对配置
        for symbol_config in config.get('trading', {}).get('symbols', []):
            symbol_config['enabled'] = symbol_config['symbol'] in args.symbols
    
    if args.timeframes:
        # 更新时间框架配置
        for tf_config in config.get('trading', {}).get('timeframes', []):
            tf_config['enabled'] = tf_config['timeframe'] in args.timeframes
    
    if args.paper:
        # 启用模拟交易
        config.setdefault('development', {})['paper_trading'] = True
    
    # 根据模式运行
    try:
        if args.mode == 'live':
            asyncio.run(run_live_trading(config))
        elif args.mode == 'backtest':
            asyncio.run(run_backtest(config, args.start_date, args.end_date))
        elif args.mode == 'optimize':
            run_optimization(config)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
