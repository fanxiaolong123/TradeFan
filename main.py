#!/usr/bin/env python3
"""
TradeFan 量化交易系统主入口
统一的启动入口，支持多种交易模式和策略
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from core.config_manager import ConfigManager
from core.logger import LoggerManager
from framework.strategy_manager import StrategyManager
from framework.portfolio import PortfolioManager
from monitoring.analytics.performance_analyzer import PerformanceAnalyzer


class TradeFanApplication:
    """TradeFan应用程序主类"""
    
    def __init__(self):
        """初始化应用程序"""
        self.config_manager = None  # 配置管理器
        self.logger_manager = None  # 日志管理器
        self.strategy_manager = None  # 策略管理器
        self.portfolio_manager = None  # 组合管理器
        self.performance_analyzer = None  # 性能分析器
        self.logger = None  # 主日志记录器
    
    async def initialize(self, config_path: str = None, environment: str = "development"):
        """
        初始化应用程序组件
        
        Args:
            config_path: 配置文件路径
            environment: 运行环境 (development/testing/production)
        """
        try:
            # 初始化配置管理器
            self.config_manager = ConfigManager(environment=environment)
            if config_path:
                self.config_manager.load_config(config_path)
            
            # 初始化日志管理器
            self.logger_manager = LoggerManager(self.config_manager)
            self.logger = self.logger_manager.get_logger("main")
            
            self.logger.info(f"TradeFan 启动中... 环境: {environment}")
            
            # 初始化策略管理器
            self.strategy_manager = StrategyManager(
                config_manager=self.config_manager,
                logger_manager=self.logger_manager
            )
            
            # 初始化组合管理器
            self.portfolio_manager = PortfolioManager(
                config_manager=self.config_manager,
                logger_manager=self.logger_manager
            )
            
            # 初始化性能分析器
            self.performance_analyzer = PerformanceAnalyzer(
                config_manager=self.config_manager,
                logger_manager=self.logger_manager
            )
            
            self.logger.info("所有组件初始化完成")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"初始化失败: {e}")
            else:
                print(f"初始化失败: {e}")
            raise
    
    async def run_backtest(self, strategy_name: str, symbols: list, start_date: str, end_date: str):
        """
        运行回测
        
        Args:
            strategy_name: 策略名称
            symbols: 交易对列表
            start_date: 开始日期
            end_date: 结束日期
        """
        self.logger.info(f"开始回测: 策略={strategy_name}, 交易对={symbols}")
        
        try:
            # 加载策略
            strategy = await self.strategy_manager.load_strategy(strategy_name)
            
            # 运行回测
            results = await strategy.run_backtest(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            # 分析结果
            analysis = await self.performance_analyzer.analyze_backtest_results(results)
            
            self.logger.info("回测完成")
            return analysis
            
        except Exception as e:
            self.logger.error(f"回测失败: {e}")
            raise
    
    async def run_live_trading(self, strategy_name: str, symbols: list, paper_trading: bool = True):
        """
        运行实盘交易
        
        Args:
            strategy_name: 策略名称
            symbols: 交易对列表
            paper_trading: 是否为模拟交易
        """
        mode = "模拟交易" if paper_trading else "实盘交易"
        self.logger.info(f"开始{mode}: 策略={strategy_name}, 交易对={symbols}")
        
        try:
            # 加载策略
            strategy = await self.strategy_manager.load_strategy(strategy_name)
            
            # 设置交易模式
            strategy.set_paper_trading(paper_trading)
            
            # 启动实时交易
            await strategy.start_live_trading(symbols)
            
        except Exception as e:
            self.logger.error(f"{mode}失败: {e}")
            raise
    
    async def run_optimization(self, strategy_name: str, symbols: list, optimization_params: dict):
        """
        运行策略优化
        
        Args:
            strategy_name: 策略名称
            symbols: 交易对列表
            optimization_params: 优化参数
        """
        self.logger.info(f"开始策略优化: {strategy_name}")
        
        try:
            # 运行优化
            results = await self.strategy_manager.optimize_strategy(
                strategy_name=strategy_name,
                symbols=symbols,
                params=optimization_params
            )
            
            self.logger.info("策略优化完成")
            return results
            
        except Exception as e:
            self.logger.error(f"策略优化失败: {e}")
            raise
    
    async def shutdown(self):
        """优雅关闭应用程序"""
        self.logger.info("正在关闭TradeFan...")
        
        try:
            # 停止所有策略
            if self.strategy_manager:
                await self.strategy_manager.stop_all_strategies()
            
            # 保存组合状态
            if self.portfolio_manager:
                await self.portfolio_manager.save_state()
            
            self.logger.info("TradeFan已安全关闭")
            
        except Exception as e:
            self.logger.error(f"关闭过程中出现错误: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TradeFan 量化交易系统")
    
    # 基本参数
    parser.add_argument("--env", default="development", 
                       choices=["development", "testing", "production"],
                       help="运行环境")
    parser.add_argument("--config", help="配置文件路径")
    
    # 运行模式
    parser.add_argument("--mode", required=True,
                       choices=["backtest", "live", "optimize", "monitor"],
                       help="运行模式")
    
    # 策略参数
    parser.add_argument("--strategy", required=True, help="策略名称")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT"], help="交易对列表")
    
    # 回测参数
    parser.add_argument("--start-date", help="回测开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="回测结束日期 (YYYY-MM-DD)")
    
    # 交易参数
    parser.add_argument("--paper", action="store_true", help="模拟交易模式")
    
    args = parser.parse_args()
    
    # 创建应用程序实例
    app = TradeFanApplication()
    
    try:
        # 初始化应用程序
        await app.initialize(config_path=args.config, environment=args.env)
        
        # 根据模式执行相应操作
        if args.mode == "backtest":
            if not args.start_date or not args.end_date:
                print("回测模式需要指定 --start-date 和 --end-date")
                sys.exit(1)
            
            results = await app.run_backtest(
                strategy_name=args.strategy,
                symbols=args.symbols,
                start_date=args.start_date,
                end_date=args.end_date
            )
            print(f"回测结果: {results}")
            
        elif args.mode == "live":
            await app.run_live_trading(
                strategy_name=args.strategy,
                symbols=args.symbols,
                paper_trading=args.paper
            )
            
        elif args.mode == "optimize":
            # 使用默认优化参数
            optimization_params = {
                "method": "grid_search",
                "iterations": 100
            }
            results = await app.run_optimization(
                strategy_name=args.strategy,
                symbols=args.symbols,
                optimization_params=optimization_params
            )
            print(f"优化结果: {results}")
            
        elif args.mode == "monitor":
            # 启动监控界面
            from monitoring.dashboard.app import start_dashboard
            await start_dashboard(app)
    
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭...")
    except Exception as e:
        print(f"运行错误: {e}")
        sys.exit(1)
    finally:
        # 优雅关闭
        await app.shutdown()


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
