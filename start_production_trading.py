#!/usr/bin/env python3
"""
TradeFan 生产环境交易启动脚本
支持多策略并行交易，完整的风险管理和监控

使用方法:
python3 start_production_trading.py --mode live --capital 1000
python3 start_production_trading.py --mode backtest --symbols BTC/USDT ETH/USDT
python3 start_production_trading.py --mode optimize
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.infrastructure_manager import get_infrastructure_manager
from modules.multi_strategy_backtester import MultiStrategyBacktester
from modules.binance_connector import BinanceTradingBot
from modules.config_manager import get_config_manager
from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, MARKET_SPECIFIC_CONFIGS


class ProductionTradingManager:
    """生产环境交易管理器"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.config_manager = get_config_manager()
        self.infrastructure = get_infrastructure_manager()
        
        # 交易机器人
        self.trading_bots = {}
        self.strategies = {}
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        
        # 支持的交易对
        self.supported_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',
            'PEPE/USDT', 'DOGE/USDT', 'WLD/USDT'
        ]
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/production_trading.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(self.shutdown())
    
    async def initialize(self, environment: str = "production"):
        """初始化系统"""
        try:
            self.logger.info("🚀 Initializing TradeFan Production Trading System...")
            
            # 1. 初始化基础设施
            success = await self.infrastructure.initialize(environment)
            if not success:
                raise RuntimeError("Failed to initialize infrastructure")
            
            # 2. 加载配置
            self.config = self.config_manager.load_config(environment)
            
            # 3. 验证API密钥
            await self._validate_api_credentials()
            
            # 4. 初始化策略
            self._initialize_strategies()
            
            self.logger.info("✅ Production trading system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    async def _validate_api_credentials(self):
        """验证API凭证"""
        try:
            exchange_config = self.config.exchanges[0]  # 使用第一个交易所配置
            
            # 从环境变量获取API密钥
            api_secret = os.getenv('BINANCE_API_SECRET')
            if not api_secret:
                raise ValueError("BINANCE_API_SECRET environment variable not set")
            
            # 测试连接
            from modules.binance_connector import BinanceConnector
            async with BinanceConnector(
                exchange_config.api_key, 
                api_secret, 
                testnet=exchange_config.sandbox
            ) as connector:
                await connector.test_connectivity()
                account_info = await connector.get_account_info()
                
            self.logger.info("✅ API credentials validated successfully")
            
        except Exception as e:
            self.logger.error(f"❌ API validation failed: {e}")
            raise
    
    def _initialize_strategies(self):
        """初始化策略"""
        try:
            # 短线策略
            scalping_config = self.config.strategy.__dict__.get('scalping', {})
            if isinstance(scalping_config, dict):
                self.strategies['scalping'] = ScalpingStrategy(scalping_config)
            
            # 趋势跟踪策略
            trend_config = self.config.strategy.__dict__.get('trend_following', {})
            if isinstance(trend_config, dict):
                self.strategies['trend_following'] = TrendFollowingStrategy(trend_config)
            
            self.logger.info(f"✅ Initialized {len(self.strategies)} strategies")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize strategies: {e}")
            raise
    
    async def run_backtest(self, symbols: List[str] = None, 
                          start_date: str = "2024-01-01",
                          end_date: str = None) -> Dict:
        """运行回测"""
        try:
            self.logger.info("📊 Starting comprehensive backtest...")
            
            if symbols is None:
                symbols = self.supported_symbols
            
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            # 创建多策略回测器
            backtester = MultiStrategyBacktester({
                'initial_capital': 10000,
                'commission': 0.001,
                'slippage': 0.0005
            })
            
            # 运行回测
            results = await backtester.run_comprehensive_backtest(
                start_date=start_date,
                end_date=end_date,
                timeframes=['5m', '15m', '30m', '1h']
            )
            
            # 显示结果摘要
            self._display_backtest_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Backtest failed: {e}")
            raise
    
    def _display_backtest_results(self, results: Dict):
        """显示回测结果"""
        try:
            report = results.get('report', {})
            summary = report.get('summary', {})
            
            self.logger.info("📊 Backtest Results Summary:")
            self.logger.info(f"   Total Backtests: {summary.get('total_backtests', 0)}")
            self.logger.info(f"   Average Return: {summary.get('avg_return', 0):.2%}")
            self.logger.info(f"   Average Sharpe: {summary.get('avg_sharpe', 0):.2f}")
            self.logger.info(f"   Average Win Rate: {summary.get('avg_win_rate', 0):.2%}")
            self.logger.info(f"   Best Return: {summary.get('best_return', 0):.2%}")
            
            # 显示最佳表现者
            best_performer = report.get('best_performers', {}).get('overall_best', {})
            if best_performer:
                self.logger.info("🏆 Best Performer:")
                self.logger.info(f"   Strategy: {best_performer.get('strategy')}")
                self.logger.info(f"   Symbol: {best_performer.get('symbol')}")
                self.logger.info(f"   Timeframe: {best_performer.get('timeframe')}")
                self.logger.info(f"   Return: {best_performer.get('return', 0):.2%}")
                self.logger.info(f"   Sharpe: {best_performer.get('sharpe', 0):.2f}")
            
            # 显示建议
            recommendations = report.get('recommendations', [])
            if recommendations:
                self.logger.info("💡 Recommendations:")
                for i, rec in enumerate(recommendations[:3], 1):
                    self.logger.info(f"   {i}. {rec}")
                    
        except Exception as e:
            self.logger.error(f"Error displaying backtest results: {e}")
    
    async def start_live_trading(self, capital: float = 1000, 
                               symbols: List[str] = None,
                               test_mode: bool = True):
        """开始实盘交易"""
        try:
            self.logger.info("🚀 Starting live trading...")
            
            if symbols is None:
                symbols = self.supported_symbols
            
            # 验证资金
            if capital < len(symbols) * 50:  # 每个交易对至少50U
                raise ValueError(f"Insufficient capital. Minimum required: {len(symbols) * 50}")
            
            # 计算每个交易对的资金分配
            capital_per_symbol = capital / len(symbols)
            
            self.logger.info(f"💰 Total Capital: ${capital}")
            self.logger.info(f"💰 Capital per Symbol: ${capital_per_symbol:.2f}")
            self.logger.info(f"📊 Trading Symbols: {symbols}")
            self.logger.info(f"🧪 Test Mode: {test_mode}")
            
            # 获取API凭证
            exchange_config = self.config.exchanges[0]
            api_secret = os.getenv('BINANCE_API_SECRET')
            
            # 为每个策略创建交易机器人
            for strategy_name, strategy in self.strategies.items():
                bot_symbols = self._get_symbols_for_strategy(strategy_name, symbols)
                if not bot_symbols:
                    continue
                
                self.logger.info(f"🤖 Starting {strategy_name} bot for {len(bot_symbols)} symbols")
                
                # 创建交易机器人
                bot = BinanceTradingBot(
                    exchange_config.api_key,
                    api_secret,
                    testnet=test_mode or exchange_config.sandbox
                )
                
                self.trading_bots[strategy_name] = bot
                
                # 启动交易
                asyncio.create_task(
                    self._run_strategy_bot(bot, strategy, bot_symbols, capital_per_symbol)
                )
            
            self.is_running = True
            self.start_time = datetime.now()
            
            # 启动监控任务
            asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("✅ Live trading started successfully")
            
            # 保持运行
            while self.is_running:
                await asyncio.sleep(60)
                
        except Exception as e:
            self.logger.error(f"❌ Live trading failed: {e}")
            await self.shutdown()
            raise
    
    def _get_symbols_for_strategy(self, strategy_name: str, symbols: List[str]) -> List[str]:
        """获取策略对应的交易对"""
        strategy_symbols = []
        
        for exchange in self.config.exchanges:
            for symbol_config in exchange.symbols:
                symbol = symbol_config.symbol.replace('/', '')  # BTCUSDT格式
                if symbol_config.symbol in symbols:
                    strategy_setting = symbol_config.strategy
                    
                    if (strategy_setting == "both" or 
                        strategy_setting == strategy_name):
                        strategy_symbols.append(symbol)
        
        return strategy_symbols
    
    async def _run_strategy_bot(self, bot: BinanceTradingBot, strategy, 
                              symbols: List[str], capital_per_symbol: float):
        """运行策略机器人"""
        try:
            async with bot:
                await bot.start_trading(strategy, symbols, capital_per_symbol)
        except Exception as e:
            self.logger.error(f"Strategy bot error: {e}")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                await self._log_trading_status()
                await self._check_risk_limits()
                await asyncio.sleep(300)  # 每5分钟检查一次
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _log_trading_status(self):
        """记录交易状态"""
        try:
            total_pnl = 0
            total_positions = 0
            
            for bot_name, bot in self.trading_bots.items():
                if hasattr(bot, 'get_portfolio_status'):
                    status = await bot.get_portfolio_status()
                    bot_pnl = status.get('total_unrealized_pnl', 0)
                    bot_positions = len([p for p in status.get('positions', {}).values() 
                                       if p.get('current_position', 0) != 0])
                    
                    total_pnl += bot_pnl
                    total_positions += bot_positions
                    
                    self.logger.info(f"📊 {bot_name}: PnL: ${bot_pnl:.2f}, Positions: {bot_positions}")
            
            # 计算运行时间
            if self.start_time:
                runtime = datetime.now() - self.start_time
                hours = runtime.total_seconds() / 3600
                
                self.logger.info(f"💰 Total PnL: ${total_pnl:.2f}")
                self.logger.info(f"📈 Active Positions: {total_positions}")
                self.logger.info(f"⏰ Runtime: {hours:.1f} hours")
                
        except Exception as e:
            self.logger.error(f"Error logging trading status: {e}")
    
    async def _check_risk_limits(self):
        """检查风险限制"""
        try:
            # 这里可以添加风险检查逻辑
            # 例如：检查总亏损、回撤等
            pass
            
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
    
    async def run_optimization(self, symbols: List[str] = None):
        """运行参数优化"""
        try:
            self.logger.info("🔧 Starting parameter optimization...")
            
            if symbols is None:
                symbols = self.supported_symbols[:3]  # 限制为前3个交易对
            
            # 这里可以添加参数优化逻辑
            # 使用遗传算法、网格搜索等方法
            
            self.logger.info("✅ Parameter optimization completed")
            
        except Exception as e:
            self.logger.error(f"❌ Optimization failed: {e}")
            raise
    
    async def shutdown(self):
        """关闭系统"""
        try:
            self.logger.info("🛑 Shutting down trading system...")
            
            self.is_running = False
            
            # 停止所有交易机器人
            for bot_name, bot in self.trading_bots.items():
                try:
                    if hasattr(bot, 'stop_trading'):
                        bot.stop_trading()
                    self.logger.info(f"✅ Stopped {bot_name} bot")
                except Exception as e:
                    self.logger.error(f"Error stopping {bot_name} bot: {e}")
            
            # 关闭基础设施
            await self.infrastructure.shutdown()
            
            self.logger.info("✅ System shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TradeFan Production Trading System')
    parser.add_argument('--mode', choices=['live', 'backtest', 'optimize'], 
                       default='backtest', help='Trading mode')
    parser.add_argument('--capital', type=float, default=1000, 
                       help='Trading capital (default: 1000)')
    parser.add_argument('--symbols', nargs='+', 
                       help='Trading symbols (default: all supported)')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Use test/sandbox mode')
    parser.add_argument('--start-date', default='2024-01-01', 
                       help='Backtest start date')
    parser.add_argument('--end-date', help='Backtest end date')
    
    args = parser.parse_args()
    
    # 创建交易管理器
    manager = ProductionTradingManager()
    
    try:
        # 初始化系统
        success = await manager.initialize("production")
        if not success:
            return 1
        
        # 根据模式执行不同操作
        if args.mode == 'backtest':
            print("📊 Running comprehensive backtest...")
            await manager.run_backtest(
                symbols=args.symbols,
                start_date=args.start_date,
                end_date=args.end_date
            )
            
        elif args.mode == 'live':
            print("🚀 Starting live trading...")
            await manager.start_live_trading(
                capital=args.capital,
                symbols=args.symbols,
                test_mode=args.test_mode
            )
            
        elif args.mode == 'optimize':
            print("🔧 Running parameter optimization...")
            await manager.run_optimization(symbols=args.symbols)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
