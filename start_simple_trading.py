#!/usr/bin/env python3
"""
TradeFan 简化交易启动脚本
快速启动双策略交易系统

使用方法:
python3 start_simple_trading.py --mode demo    # 演示模式
python3 start_simple_trading.py --mode test    # 测试模式
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, DEFAULT_TREND_CONFIG


class SimpleTradingManager:
    """简化交易管理器"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.is_running = False
        self.strategies = {}
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到停止信号 {signum}，正在优雅关闭...")
        self.is_running = False
    
    def initialize_strategies(self):
        """初始化策略"""
        try:
            # 短线策略
            scalping_config = {
                'ema_fast': 8,
                'ema_medium': 21,
                'ema_slow': 55,
                'rsi_period': 14,
                'signal_threshold': 0.6
            }
            self.strategies['scalping'] = ScalpingStrategy(**scalping_config)
            
            # 趋势策略
            self.strategies['trend'] = TrendFollowingStrategy(DEFAULT_TREND_CONFIG)
            
            self.logger.info(f"✅ 初始化了 {len(self.strategies)} 个策略")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 策略初始化失败: {e}")
            return False
    
    async def run_demo_mode(self):
        """运行演示模式"""
        self.logger.info("🎬 启动演示模式...")
        
        # 交易对配置
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        capital_per_symbol = 500  # 每个交易对500U
        
        self.logger.info(f"💰 模拟资金: ${len(symbols) * capital_per_symbol}")
        self.logger.info(f"📊 交易对: {symbols}")
        self.logger.info(f"🎯 策略: {list(self.strategies.keys())}")
        
        self.is_running = True
        cycle_count = 0
        
        try:
            while self.is_running:
                cycle_count += 1
                self.logger.info(f"\n🔄 交易周期 #{cycle_count}")
                
                for symbol in symbols:
                    for strategy_name, strategy in self.strategies.items():
                        # 模拟获取市场数据
                        current_price = self._get_mock_price(symbol)
                        
                        # 模拟信号生成
                        signal = self._generate_mock_signal(strategy_name)
                        
                        # 模拟交易执行
                        if signal in ['BUY', 'SELL']:
                            self.logger.info(f"📈 {strategy_name} 策略 - {symbol}: {signal} @ ${current_price:.2f}")
                            
                            # 模拟订单执行
                            await self._simulate_order_execution(symbol, signal, current_price, capital_per_symbol)
                
                # 显示模拟统计
                await self._show_demo_stats(cycle_count)
                
                # 等待下一个周期
                await asyncio.sleep(30)  # 30秒一个周期
                
        except KeyboardInterrupt:
            self.logger.info("⚠️ 演示被用户中断")
        except Exception as e:
            self.logger.error(f"❌ 演示模式出错: {e}")
        finally:
            self.is_running = False
    
    def _get_mock_price(self, symbol):
        """获取模拟价格"""
        import random
        base_prices = {
            "BTCUSDT": 45000,
            "ETHUSDT": 3000,
            "BNBUSDT": 300
        }
        base_price = base_prices.get(symbol, 1000)
        # 添加±2%的随机波动
        return base_price * (1 + random.uniform(-0.02, 0.02))
    
    def _generate_mock_signal(self, strategy_name):
        """生成模拟信号"""
        import random
        
        if strategy_name == 'scalping':
            # 短线策略更频繁的信号
            signals = ['BUY', 'SELL', 'HOLD', 'HOLD']
        else:
            # 趋势策略较少的信号
            signals = ['BUY', 'SELL', 'HOLD', 'HOLD', 'HOLD', 'HOLD']
        
        return random.choice(signals)
    
    async def _simulate_order_execution(self, symbol, signal, price, capital):
        """模拟订单执行"""
        quantity = (capital * 0.1) / price  # 使用10%资金
        
        # 模拟执行延迟
        await asyncio.sleep(0.1)
        
        # 模拟滑点
        import random
        slippage = random.uniform(0.0001, 0.001)  # 0.01%-0.1%滑点
        execution_price = price * (1 + slippage if signal == 'BUY' else 1 - slippage)
        
        self.logger.info(f"   ✅ 模拟执行: {signal} {quantity:.4f} {symbol} @ ${execution_price:.2f}")
    
    async def _show_demo_stats(self, cycle_count):
        """显示演示统计"""
        if cycle_count % 5 == 0:  # 每5个周期显示一次统计
            import random
            
            # 模拟统计数据
            total_trades = cycle_count * 2  # 假设每周期2笔交易
            win_rate = random.uniform(0.55, 0.75)  # 55%-75%胜率
            total_pnl = random.uniform(-100, 200)  # -100到+200的PnL
            
            self.logger.info(f"\n📊 演示统计 (周期 #{cycle_count}):")
            self.logger.info(f"   💰 模拟总PnL: ${total_pnl:.2f}")
            self.logger.info(f"   📈 模拟胜率: {win_rate:.1%}")
            self.logger.info(f"   📋 模拟交易数: {total_trades}")
            self.logger.info(f"   ⏰ 运行时间: {cycle_count * 0.5:.1f} 分钟")
    
    async def run_test_mode(self):
        """运行测试模式"""
        self.logger.info("🧪 启动测试模式...")
        
        # 这里可以集成真实的Binance测试网API
        self.logger.info("⚠️ 测试模式需要配置Binance API")
        self.logger.info("💡 请先设置 BINANCE_API_SECRET 环境变量")
        
        api_secret = os.getenv('BINANCE_API_SECRET')
        if not api_secret or api_secret == "placeholder_secret_for_testing":
            self.logger.warning("❌ 未配置有效的API密钥，切换到演示模式")
            await self.run_demo_mode()
            return
        
        # 如果有有效API密钥，这里可以启动真实测试
        self.logger.info("🚀 启动真实测试网交易...")
        self.logger.info("⚠️ 真实测试功能开发中，当前运行演示模式")
        await self.run_demo_mode()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TradeFan 简化交易系统')
    parser.add_argument('--mode', choices=['demo', 'test'], default='demo',
                       help='运行模式: demo=演示模式, test=测试网模式')
    
    args = parser.parse_args()
    
    print("🚀 TradeFan 简化交易系统")
    print("=" * 40)
    
    manager = SimpleTradingManager()
    
    try:
        # 初始化策略
        if not manager.initialize_strategies():
            print("❌ 策略初始化失败")
            return 1
        
        # 根据模式运行
        if args.mode == 'demo':
            print("🎬 启动演示模式 (模拟交易)")
            print("💡 这是安全的演示模式，不会进行真实交易")
            print("⏰ 按 Ctrl+C 停止演示")
            print()
            await manager.run_demo_mode()
        
        elif args.mode == 'test':
            print("🧪 启动测试模式 (测试网)")
            print("💡 这将连接到Binance测试网进行真实测试")
            print("⏰ 按 Ctrl+C 停止测试")
            print()
            await manager.run_test_mode()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ 程序被用户中断")
        return 0
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 再见!")
        sys.exit(0)
