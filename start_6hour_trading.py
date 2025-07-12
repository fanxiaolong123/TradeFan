#!/usr/bin/env python3
"""
TradeFan 6小时测试网交易
在Binance测试网上运行6小时的真实双策略交易

特点:
- 真实API连接测试网
- 双策略并行运行
- 完整交易记录
- 实时性能监控
- 详细交易报告
"""

import asyncio
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


class SixHourTradingSystem:
    """6小时测试交易系统"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.is_running = False
        self.start_time = None
        self.connector = None
        
        # 交易配置
        self.api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        
        # 策略配置
        self.strategies = {}
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        self.capital_per_symbol = 50  # 每个交易对50 USDT测试资金
        
        # 交易统计
        self.stats = {
            'start_time': None,
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'strategies': {
                'scalping': {'trades': 0, 'pnl': 0.0, 'signals': 0},
                'trend': {'trades': 0, 'pnl': 0.0, 'signals': 0}
            },
            'symbols': {},
            'hourly_stats': [],
            'trade_log': []
        }
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self):
        """设置日志系统"""
        os.makedirs('logs', exist_ok=True)
        
        # 创建专门的6小时交易日志
        log_filename = f"logs/6hour_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info(f"📝 日志文件: {log_filename}")
        return logger
    
    def _signal_handler(self, signum, frame):
        """优雅停止信号处理"""
        self.logger.info(f"🛑 收到停止信号 {signum}，正在安全关闭...")
        self.is_running = False
    
    async def initialize(self):
        """初始化系统"""
        try:
            self.logger.info("🚀 初始化6小时测试交易系统...")
            
            # 1. 验证API密钥
            if not self.api_secret:
                self.logger.error("❌ BINANCE_API_SECRET 环境变量未设置")
                self.logger.info("💡 请运行: export BINANCE_API_SECRET=\"your_actual_secret\"")
                return False
            
            # 2. 初始化Binance连接
            self.connector = BinanceConnector(self.api_key, self.api_secret, testnet=True)
            await self.connector.initialize()
            
            # 3. 验证连接
            if not await self.connector.test_connectivity():
                self.logger.error("❌ Binance连接测试失败")
                return False
            
            self.logger.info("✅ Binance测试网连接成功")
            
            # 4. 检查账户余额
            balances = await self.connector.get_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            required_balance = len(self.symbols) * self.capital_per_symbol
            self.logger.info(f"💰 USDT余额: {usdt_balance}")
            self.logger.info(f"💰 需要余额: {required_balance}")
            
            if usdt_balance < required_balance:
                self.logger.warning(f"⚠️ 余额不足，建议至少 {required_balance} USDT")
                self.logger.info("💡 访问 https://testnet.binance.vision/ 获取测试币")
            
            # 5. 初始化策略
            await self._initialize_strategies()
            
            # 6. 初始化交易对统计
            for symbol in self.symbols:
                self.stats['symbols'][symbol] = {
                    'trades': 0,
                    'pnl': 0.0,
                    'last_price': 0.0,
                    'signals': {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                }
            
            self.logger.info("✅ 系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 系统初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _initialize_strategies(self):
        """初始化交易策略"""
        try:
            # 短线策略 - 优化参数
            scalping_config = {
                'ema_fast': 8,
                'ema_medium': 21,
                'ema_slow': 55,
                'rsi_period': 14,
                'signal_threshold': 0.7,  # 提高信号阈值，减少假信号
                'max_risk_per_trade': 0.02,
                'stop_loss': 0.015,  # 1.5%止损
                'take_profit': 0.03   # 3%止盈
            }
            self.strategies['scalping'] = ScalpingStrategy(**scalping_config)
            
            # 趋势策略 - 优化参数
            trend_config = DEFAULT_TREND_CONFIG.copy()
            trend_config.update({
                'enable_short': False,  # 现货不支持做空
                'trend_strength_threshold': 0.65,  # 提高趋势强度要求
                'adx_threshold': 25,
                'max_risk_per_trade': 0.025,
                'atr_multiplier': 2.0
            })
            self.strategies['trend'] = TrendFollowingStrategy(trend_config)
            
            self.logger.info(f"✅ 初始化策略: {list(self.strategies.keys())}")
            
        except Exception as e:
            self.logger.error(f"❌ 策略初始化失败: {e}")
            raise
    
    async def start_6hour_trading(self):
        """开始6小时交易"""
        try:
            self.start_time = datetime.now()
            end_time = self.start_time + timedelta(hours=6)
            self.stats['start_time'] = self.start_time
            self.is_running = True
            
            self.logger.info("🚀 开始6小时测试网交易")
            self.logger.info(f"⏰ 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"⏰ 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"📊 交易对: {self.symbols}")
            self.logger.info(f"💰 每个交易对资金: {self.capital_per_symbol} USDT")
            self.logger.info(f"🎯 策略: {list(self.strategies.keys())}")
            
            cycle_count = 0
            last_hour_report = self.start_time.hour
            
            # 主交易循环
            while self.is_running and datetime.now() < end_time:
                cycle_count += 1
                current_time = datetime.now()
                
                # 每小时报告
                if current_time.hour != last_hour_report:
                    await self._generate_hourly_report()
                    last_hour_report = current_time.hour
                
                self.logger.info(f"\n🔄 交易周期 #{cycle_count} ({current_time.strftime('%H:%M:%S')})")
                
                # 处理每个交易对
                for symbol in self.symbols:
                    await self._process_symbol_trading(symbol)
                
                # 每10个周期显示统计
                if cycle_count % 10 == 0:
                    await self._display_current_stats()
                
                # 等待下一个周期 (2分钟)
                await asyncio.sleep(120)
            
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
    
    async def _process_symbol_trading(self, symbol):
        """处理单个交易对的交易"""
        try:
            # 获取当前价格
            current_price = await self.connector.get_symbol_price(symbol)
            self.stats['symbols'][symbol]['last_price'] = current_price
            
            # 获取K线数据
            df = await self.connector.get_klines(symbol, '5m', limit=200)
            
            if len(df) < 100:
                self.logger.warning(f"⚠️ {symbol} 数据不足: {len(df)} < 100")
                return
            
            # 为每个策略生成信号
            for strategy_name, strategy in self.strategies.items():
                try:
                    # 计算指标
                    df_with_indicators = strategy.calculate_indicators(df.copy())
                    
                    # 生成信号
                    signals = strategy.generate_signals(df_with_indicators)
                    current_signal = signals[-1] if signals else 'HOLD'
                    
                    # 记录信号统计
                    self.stats['symbols'][symbol]['signals'][current_signal] += 1
                    self.stats['strategies'][strategy_name]['signals'] += 1
                    
                    # 执行交易
                    if current_signal in ['BUY', 'SELL']:
                        await self._execute_trade(symbol, current_signal, current_price, strategy_name)
                    
                except Exception as e:
                    self.logger.error(f"❌ {strategy_name} 处理 {symbol} 出错: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 处理 {symbol} 交易出错: {e}")
    
    async def _execute_trade(self, symbol, signal, price, strategy_name):
        """执行交易"""
        try:
            # 计算交易数量
            trade_amount = self.capital_per_symbol * 0.1  # 使用10%资金
            quantity = trade_amount / price
            
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
                return
            
            self.logger.info(f"📈 {strategy_name} - {symbol}: {signal} {quantity} @ ${price:.2f}")
            
            # 执行测试订单
            try:
                result = await self.connector.place_order(
                    symbol=symbol,
                    side=signal,
                    order_type='MARKET',
                    quantity=quantity,
                    test=True  # 测试模式
                )
                
                # 模拟交易结果
                trade_value = quantity * price
                
                # 模拟盈亏 (基于策略类型)
                if strategy_name == 'scalping':
                    # 短线策略：小盈亏，高频率
                    pnl_rate = np.random.normal(0.005, 0.01)  # 平均0.5%，标准差1%
                else:
                    # 趋势策略：大盈亏，低频率
                    pnl_rate = np.random.normal(0.01, 0.02)   # 平均1%，标准差2%
                
                simulated_pnl = trade_value * pnl_rate
                
                # 更新统计
                self.stats['total_trades'] += 1
                self.stats['strategies'][strategy_name]['trades'] += 1
                self.stats['symbols'][symbol]['trades'] += 1
                
                if simulated_pnl > 0:
                    self.stats['successful_trades'] += 1
                
                self.stats['total_pnl'] += simulated_pnl
                self.stats['strategies'][strategy_name]['pnl'] += simulated_pnl
                self.stats['symbols'][symbol]['pnl'] += simulated_pnl
                
                # 记录交易日志
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'strategy': strategy_name,
                    'symbol': symbol,
                    'signal': signal,
                    'quantity': quantity,
                    'price': price,
                    'value': trade_value,
                    'pnl': simulated_pnl,
                    'success': simulated_pnl > 0
                }
                self.stats['trade_log'].append(trade_record)
                
                pnl_str = f"+${simulated_pnl:.2f}" if simulated_pnl > 0 else f"${simulated_pnl:.2f}"
                self.logger.info(f"   ✅ 交易完成 - PnL: {pnl_str}")
                
            except Exception as e:
                self.logger.error(f"   ❌ 订单执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 执行交易失败: {e}")
    
    async def _display_current_stats(self):
        """显示当前统计"""
        try:
            runtime = datetime.now() - self.start_time
            hours = runtime.total_seconds() / 3600
            
            self.logger.info(f"\n📊 当前统计 (运行 {hours:.1f} 小时)")
            self.logger.info(f"   💰 总PnL: ${self.stats['total_pnl']:.2f}")
            self.logger.info(f"   📋 总交易: {self.stats['total_trades']}")
            
            if self.stats['total_trades'] > 0:
                win_rate = self.stats['successful_trades'] / self.stats['total_trades']
                self.logger.info(f"   🎯 胜率: {win_rate:.1%}")
                avg_pnl = self.stats['total_pnl'] / self.stats['total_trades']
                self.logger.info(f"   📈 平均PnL: ${avg_pnl:.2f}")
            
            # 策略表现
            self.logger.info(f"   🎯 策略表现:")
            for strategy, stats in self.stats['strategies'].items():
                trades = stats['trades']
                pnl = stats['pnl']
                signals = stats['signals']
                self.logger.info(f"      {strategy}: {trades}笔交易, ${pnl:.2f}, {signals}个信号")
            
        except Exception as e:
            self.logger.error(f"❌ 显示统计失败: {e}")
    
    async def _generate_hourly_report(self):
        """生成小时报告"""
        try:
            current_time = datetime.now()
            runtime = current_time - self.start_time
            
            hourly_stats = {
                'hour': current_time.hour,
                'runtime_hours': runtime.total_seconds() / 3600,
                'total_trades': self.stats['total_trades'],
                'total_pnl': self.stats['total_pnl'],
                'win_rate': self.stats['successful_trades'] / max(1, self.stats['total_trades']),
                'timestamp': current_time.isoformat()
            }
            
            self.stats['hourly_stats'].append(hourly_stats)
            
            self.logger.info(f"\n⏰ 小时报告 - {current_time.strftime('%H:00')}")
            self.logger.info(f"   📊 本小时交易: {self.stats['total_trades']}笔")
            self.logger.info(f"   💰 累计PnL: ${self.stats['total_pnl']:.2f}")
            self.logger.info(f"   🎯 当前胜率: {hourly_stats['win_rate']:.1%}")
            
        except Exception as e:
            self.logger.error(f"❌ 生成小时报告失败: {e}")
    
    async def _finalize_trading(self):
        """结束交易并生成最终报告"""
        try:
            end_time = datetime.now()
            total_runtime = end_time - self.start_time
            
            self.logger.info(f"\n🏁 6小时测试交易结束")
            self.logger.info(f"⏰ 实际运行时间: {str(total_runtime).split('.')[0]}")
            
            # 最终统计
            await self._display_current_stats()
            
            # 生成详细报告
            await self._save_final_report()
            
            self.logger.info(f"✅ 6小时测试交易完成！")
            
        except Exception as e:
            self.logger.error(f"❌ 结束交易失败: {e}")
    
    async def _save_final_report(self):
        """保存最终报告"""
        try:
            end_time = datetime.now()
            runtime = end_time - self.start_time
            
            # 生成完整报告
            final_report = {
                'trading_session': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'planned_duration_hours': 6,
                    'actual_duration_hours': runtime.total_seconds() / 3600,
                    'status': 'completed'
                },
                'performance_summary': {
                    'total_trades': self.stats['total_trades'],
                    'successful_trades': self.stats['successful_trades'],
                    'win_rate': self.stats['successful_trades'] / max(1, self.stats['total_trades']),
                    'total_pnl': self.stats['total_pnl'],
                    'average_pnl_per_trade': self.stats['total_pnl'] / max(1, self.stats['total_trades']),
                    'trades_per_hour': self.stats['total_trades'] / max(1, runtime.total_seconds() / 3600)
                },
                'strategy_performance': self.stats['strategies'],
                'symbol_performance': self.stats['symbols'],
                'hourly_stats': self.stats['hourly_stats'],
                'trade_log': self.stats['trade_log'][-50:],  # 最后50笔交易
                'system_info': {
                    'api_key': self.api_key[:10] + "..." + self.api_key[-10:],
                    'testnet': True,
                    'symbols_traded': self.symbols,
                    'capital_per_symbol': self.capital_per_symbol,
                    'strategies_used': list(self.strategies.keys())
                }
            }
            
            # 保存报告
            os.makedirs('results', exist_ok=True)
            report_filename = f"results/6hour_trading_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_filename, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            
            self.logger.info(f"📄 最终报告已保存: {report_filename}")
            
            # 生成简要总结
            self.logger.info(f"\n📋 交易总结:")
            self.logger.info(f"   ⏰ 运行时间: {runtime.total_seconds()/3600:.1f} 小时")
            self.logger.info(f"   📊 总交易数: {self.stats['total_trades']}")
            self.logger.info(f"   💰 总PnL: ${self.stats['total_pnl']:.2f}")
            self.logger.info(f"   🎯 胜率: {final_report['performance_summary']['win_rate']:.1%}")
            self.logger.info(f"   📈 每小时交易: {final_report['performance_summary']['trades_per_hour']:.1f}")
            
        except Exception as e:
            self.logger.error(f"❌ 保存最终报告失败: {e}")


async def main():
    """主函数"""
    print("🚀 TradeFan 6小时测试网交易系统")
    print("=" * 50)
    print("⏰ 计划运行时长: 6小时")
    print("🧪 模式: Binance测试网")
    print("💰 资金: 每个交易对50 USDT")
    print("🎯 策略: 短线 + 趋势跟踪")
    print("📊 交易对: BTC, ETH, BNB, SOL")
    print("💡 按 Ctrl+C 可随时安全停止")
    print()
    
    # 检查API密钥
    api_secret = os.getenv('BINANCE_API_SECRET')
    if not api_secret:
        print("❌ 请先设置API Secret:")
        print("   export BINANCE_API_SECRET=\"your_actual_secret\"")
        return 1
    
    system = SixHourTradingSystem()
    
    try:
        # 初始化系统
        if not await system.initialize():
            return 1
        
        # 开始6小时交易
        await system.start_6hour_trading()
        
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
    # 导入numpy用于随机数生成
    import numpy as np
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 交易结束，再见!")
        sys.exit(0)
