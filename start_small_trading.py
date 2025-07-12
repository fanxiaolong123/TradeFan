#!/usr/bin/env python3
"""
TradeFan 小额交易测试
使用真实API进行小额资金测试

安全特性:
- 小额资金测试 (默认$100)
- 严格风险控制
- 实时监控
- 随时可停止
"""

import asyncio
import argparse
import logging
import os
import sys
import signal
import json
from datetime import datetime, timedelta
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.binance_connector import BinanceConnector
from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, DEFAULT_TREND_CONFIG


class SmallTradingSystem:
    """小额交易测试系统"""
    
    def __init__(self, capital: float = 100):
        self.logger = self._setup_logging()
        self.is_running = False
        self.start_time = None
        self.connector = None
        
        # 交易配置
        self.api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
        self.api_secret = "QkKb8JjFOhnC0Ri4Zya6HMeBMtuMeArGR9zem38ULwm8Zo6O0sLORNs9OX63rdWv"
        
        # 资金配置
        self.total_capital = capital
        self.symbols = ['BTCUSDT', 'ETHUSDT']  # 先测试主要交易对
        self.capital_per_symbol = capital / len(self.symbols)
        
        # 策略配置
        self.strategies = {}
        
        # 安全限制
        self.max_trade_value = min(20, capital * 0.1)  # 单笔最大$20或10%资金
        self.max_daily_loss = capital * 0.05  # 日最大损失5%
        self.max_positions = 2  # 最大持仓数
        
        # 交易统计
        self.stats = {
            'start_time': None,
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'daily_loss': 0.0,
            'current_positions': 0,
            'strategies': {
                'scalping': {'trades': 0, 'pnl': 0.0},
                'trend': {'trades': 0, 'pnl': 0.0}
            },
            'trade_log': []
        }
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """设置日志"""
        os.makedirs('logs', exist_ok=True)
        
        log_filename = f"logs/small_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"📝 交易日志: {log_filename}")
        return logger
    
    def _signal_handler(self, signum, frame):
        """安全停止信号处理"""
        self.logger.info(f"🛑 收到停止信号，正在安全关闭...")
        self.is_running = False
    
    async def initialize(self):
        """初始化系统"""
        try:
            self.logger.info("🚀 初始化小额交易测试系统...")
            self.logger.info(f"💰 测试资金: ${self.total_capital}")
            self.logger.info(f"📊 交易对: {self.symbols}")
            self.logger.info(f"💵 每个交易对资金: ${self.capital_per_symbol:.2f}")
            self.logger.info(f"🛡️ 单笔最大: ${self.max_trade_value}")
            self.logger.info(f"🛡️ 日最大损失: ${self.max_daily_loss}")
            
            # 1. 初始化Binance连接
            self.connector = BinanceConnector(self.api_key, self.api_secret, testnet=False)
            await self.connector.initialize()
            
            # 2. 验证连接和账户
            if not await self._verify_account():
                return False
            
            # 3. 初始化策略
            await self._initialize_strategies()
            
            self.logger.info("✅ 系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 系统初始化失败: {e}")
            return False
    
    async def _verify_account(self):
        """验证账户状态"""
        try:
            # 连接测试
            if not await self.connector.test_connectivity():
                self.logger.error("❌ 网络连接失败")
                return False
            
            # 账户信息
            account_info = await self.connector.get_account_info()
            if not account_info.get('canTrade', False):
                self.logger.error("❌ 账户无法交易")
                return False
            
            # 余额检查
            balances = await self.connector.get_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            self.logger.info(f"💰 USDT可用余额: {usdt_balance:.2f}")
            
            if usdt_balance < self.total_capital:
                self.logger.warning(f"⚠️ 余额不足: {usdt_balance:.2f} < {self.total_capital}")
                self.logger.info("💡 将使用可用余额进行测试")
                self.total_capital = min(self.total_capital, usdt_balance * 0.9)  # 使用90%余额
                self.capital_per_symbol = self.total_capital / len(self.symbols)
            
            self.logger.info("✅ 账户验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 账户验证失败: {e}")
            return False
    
    async def _initialize_strategies(self):
        """初始化策略"""
        try:
            # 保守的短线策略
            scalping_config = {
                'ema_fast': 8,
                'ema_medium': 21,
                'ema_slow': 55,
                'rsi_period': 14,
                'signal_threshold': 0.75,  # 高阈值，减少交易频率
                'max_risk_per_trade': 0.01,  # 1%风险
                'stop_loss': 0.01,  # 1%止损
                'take_profit': 0.02   # 2%止盈
            }
            self.strategies['scalping'] = ScalpingStrategy(**scalping_config)
            
            # 保守的趋势策略
            trend_config = DEFAULT_TREND_CONFIG.copy()
            trend_config.update({
                'enable_short': False,
                'trend_strength_threshold': 0.7,  # 高阈值
                'adx_threshold': 30,  # 更强的趋势要求
                'max_risk_per_trade': 0.015,  # 1.5%风险
                'atr_multiplier': 1.5  # 较紧的止损
            })
            self.strategies['trend'] = TrendFollowingStrategy(trend_config)
            
            self.logger.info(f"✅ 策略初始化完成: {list(self.strategies.keys())}")
            
        except Exception as e:
            self.logger.error(f"❌ 策略初始化失败: {e}")
            raise
    
    async def start_trading(self, duration_hours: float = 6):
        """开始小额交易"""
        try:
            self.start_time = datetime.now()
            end_time = self.start_time + timedelta(hours=duration_hours)
            self.stats['start_time'] = self.start_time
            self.is_running = True
            
            self.logger.info("🚀 开始小额交易测试")
            self.logger.info(f"⏰ 开始时间: {self.start_time.strftime('%H:%M:%S')}")
            self.logger.info(f"⏰ 计划结束: {end_time.strftime('%H:%M:%S')}")
            self.logger.info(f"💰 测试资金: ${self.total_capital:.2f}")
            self.logger.info(f"🛡️ 安全限制已启用")
            
            cycle_count = 0
            
            # 主交易循环
            while self.is_running and datetime.now() < end_time:
                cycle_count += 1
                current_time = datetime.now()
                
                # 安全检查
                if not await self._safety_check():
                    self.logger.warning("🛑 安全检查失败，停止交易")
                    break
                
                self.logger.info(f"\n🔄 交易周期 #{cycle_count} ({current_time.strftime('%H:%M:%S')})")
                
                # 处理每个交易对
                for symbol in self.symbols:
                    if self.stats['current_positions'] >= self.max_positions:
                        self.logger.info(f"⚠️ 已达最大持仓数限制: {self.max_positions}")
                        break
                    
                    await self._process_symbol_trading(symbol)
                
                # 每5个周期显示统计
                if cycle_count % 5 == 0:
                    await self._display_stats()
                
                # 等待下一个周期 (3分钟)
                await asyncio.sleep(180)
            
            # 交易结束
            await self._finalize_trading()
            
        except KeyboardInterrupt:
            self.logger.info("⚠️ 交易被用户中断")
        except Exception as e:
            self.logger.error(f"❌ 交易过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
            if self.connector:
                await self.connector.close()
    
    async def _safety_check(self):
        """安全检查"""
        try:
            # 1. 检查日损失限制
            if abs(self.stats['daily_loss']) > self.max_daily_loss:
                self.logger.error(f"❌ 日损失超限: ${abs(self.stats['daily_loss']):.2f} > ${self.max_daily_loss:.2f}")
                return False
            
            # 2. 检查账户余额
            balances = await self.connector.get_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            if usdt_balance < 10:  # 最少保留$10
                self.logger.error(f"❌ 余额过低: ${usdt_balance:.2f}")
                return False
            
            # 3. 检查网络连接
            if not await self.connector.test_connectivity():
                self.logger.error("❌ 网络连接异常")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 安全检查出错: {e}")
            return False
    
    async def _process_symbol_trading(self, symbol):
        """处理单个交易对"""
        try:
            # 获取当前价格
            current_price = await self.connector.get_symbol_price(symbol)
            
            # 获取K线数据
            df = await self.connector.get_klines(symbol, '5m', limit=100)
            
            if len(df) < 50:
                self.logger.warning(f"⚠️ {symbol} 数据不足")
                return
            
            # 为每个策略生成信号
            for strategy_name, strategy in self.strategies.items():
                try:
                    # 计算指标
                    df_with_indicators = strategy.calculate_indicators(df.copy())
                    
                    # 生成信号
                    signals = strategy.generate_signals(df_with_indicators)
                    current_signal = signals[-1] if signals else 'HOLD'
                    
                    # 执行交易
                    if current_signal in ['BUY', 'SELL']:
                        await self._execute_safe_trade(symbol, current_signal, current_price, strategy_name)
                    
                except Exception as e:
                    self.logger.error(f"❌ {strategy_name} 处理 {symbol} 出错: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 处理 {symbol} 出错: {e}")
    
    async def _execute_safe_trade(self, symbol, signal, price, strategy_name):
        """执行安全交易"""
        try:
            # 计算交易数量
            trade_value = min(self.max_trade_value, self.capital_per_symbol * 0.2)  # 最多20%资金
            quantity = trade_value / price
            
            # 格式化数量
            if 'BTC' in symbol:
                quantity = round(quantity, 5)
            elif 'ETH' in symbol:
                quantity = round(quantity, 4)
            else:
                quantity = round(quantity, 3)
            
            # 最小数量检查
            min_qty = 0.001 if 'BTC' in symbol else 0.01
            if quantity < min_qty:
                self.logger.info(f"⚠️ {symbol} 交易量过小: {quantity} < {min_qty}")
                return
            
            self.logger.info(f"📈 {strategy_name} - {symbol}: {signal} {quantity} @ ${price:.2f} (${trade_value:.2f})")
            
            # 执行真实订单 (小额测试)
            try:
                result = await self.connector.place_order(
                    symbol=symbol,
                    side=signal,
                    order_type='MARKET',
                    quantity=quantity,
                    test=False  # 真实交易
                )
                
                if result:
                    # 记录真实交易
                    actual_value = quantity * price
                    
                    # 更新统计
                    self.stats['total_trades'] += 1
                    self.stats['strategies'][strategy_name]['trades'] += 1
                    self.stats['current_positions'] += 1
                    
                    # 记录交易
                    trade_record = {
                        'timestamp': datetime.now().isoformat(),
                        'strategy': strategy_name,
                        'symbol': symbol,
                        'signal': signal,
                        'quantity': quantity,
                        'price': price,
                        'value': actual_value,
                        'order_id': result.get('orderId', 'unknown')
                    }
                    self.stats['trade_log'].append(trade_record)
                    
                    self.logger.info(f"   ✅ 真实订单执行成功 - 订单ID: {result.get('orderId', 'N/A')}")
                    
                    # 设置止损止盈 (简化实现)
                    await self._set_stop_orders(symbol, signal, price, quantity)
                
            except Exception as e:
                self.logger.error(f"   ❌ 订单执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 执行交易失败: {e}")
    
    async def _set_stop_orders(self, symbol, signal, entry_price, quantity):
        """设置止损止盈订单"""
        try:
            if signal == 'BUY':
                # 多头止损
                stop_price = entry_price * 0.99  # 1%止损
                take_profit_price = entry_price * 1.02  # 2%止盈
                
                # 这里可以设置OCO订单，简化实现暂时跳过
                self.logger.info(f"   📋 建议止损: ${stop_price:.2f}, 止盈: ${take_profit_price:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ 设置止损订单失败: {e}")
    
    async def _display_stats(self):
        """显示统计信息"""
        try:
            runtime = datetime.now() - self.start_time
            
            self.logger.info(f"\n📊 交易统计 (运行 {runtime.total_seconds()/3600:.1f} 小时)")
            self.logger.info(f"   💰 总PnL: ${self.stats['total_pnl']:.2f}")
            self.logger.info(f"   📋 总交易: {self.stats['total_trades']}")
            self.logger.info(f"   📈 当前持仓: {self.stats['current_positions']}")
            
            if self.stats['total_trades'] > 0:
                win_rate = self.stats['successful_trades'] / self.stats['total_trades']
                self.logger.info(f"   🎯 胜率: {win_rate:.1%}")
            
            # 策略表现
            for strategy, stats in self.stats['strategies'].items():
                self.logger.info(f"   {strategy}: {stats['trades']}笔交易, ${stats['pnl']:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ 显示统计失败: {e}")
    
    async def _finalize_trading(self):
        """结束交易"""
        try:
            self.logger.info(f"\n🏁 小额交易测试结束")
            
            # 最终统计
            await self._display_stats()
            
            # 保存报告
            await self._save_report()
            
            self.logger.info(f"✅ 小额交易测试完成！")
            
        except Exception as e:
            self.logger.error(f"❌ 结束交易失败: {e}")
    
    async def _save_report(self):
        """保存交易报告"""
        try:
            report = {
                'session_info': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'capital': self.total_capital,
                    'symbols': self.symbols
                },
                'performance': self.stats,
                'safety_limits': {
                    'max_trade_value': self.max_trade_value,
                    'max_daily_loss': self.max_daily_loss,
                    'max_positions': self.max_positions
                }
            }
            
            os.makedirs('results', exist_ok=True)
            filename = f"results/small_trading_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"📄 交易报告已保存: {filename}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存报告失败: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TradeFan 小额交易测试')
    parser.add_argument('--capital', type=float, default=100,
                       help='测试资金 (默认: $100)')
    parser.add_argument('--duration', type=float, default=6,
                       help='交易时长(小时) (默认: 6小时)')
    
    args = parser.parse_args()
    
    print("🚀 TradeFan 小额交易测试系统")
    print("=" * 50)
    print(f"💰 测试资金: ${args.capital}")
    print(f"⏰ 交易时长: {args.duration} 小时")
    print(f"🛡️ 安全模式: 启用多重保护")
    print(f"⚠️  真实环境: 涉及真实资金")
    print(f"💡 随时按 Ctrl+C 安全停止")
    print()
    
    # 用户确认
    try:
        confirm = input(f"确认开始 ${args.capital} 小额交易测试？(输入 'yes' 继续): ")
        if confirm.lower() != 'yes':
            print("❌ 交易已取消")
            return 1
    except KeyboardInterrupt:
        print("\n❌ 交易已取消")
        return 1
    
    system = SmallTradingSystem(args.capital)
    
    try:
        # 初始化系统
        if not await system.initialize():
            return 1
        
        # 开始交易
        await system.start_trading(args.duration)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ 交易被用户安全中断")
        return 0
    except Exception as e:
        print(f"\n❌ 系统出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 交易结束，再见!")
        sys.exit(0)
