#!/usr/bin/env python3
"""
实盘模拟交易主程序
支持实时行情驱动的策略执行
"""

import asyncio
import signal
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils import ConfigLoader
from modules.log_module import LogModule
from modules.strategy_module import StrategyManager
from modules.risk_control_module import RiskControlModule
from modules.live_execution_module import LiveExecutionModule
from modules.data_module import DataModule
from modules.monitor_module import MonitorModule

class LiveTradingSystem:
    """实盘模拟交易系统"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # 加载配置
        self.config = ConfigLoader(config_path)
        
        # 初始化日志
        self.logger = LogModule()
        self.logger.info("=" * 60)
        self.logger.info("🚀 启动实盘模拟交易系统")
        self.logger.info("=" * 60)
        
        # 系统状态
        self.running = False
        self.last_signal_time = {}
        
        # 初始化模块
        self._init_modules()
        
        # 价格数据缓存
        self.price_data = {}
        self.last_prices = {}
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _init_modules(self):
        """初始化各个模块"""
        try:
            # 数据模块
            self.data_module = DataModule(self.config.config, logger=self.logger)
            
            # 策略模块
            self.strategy_manager = StrategyManager(logger=self.logger)
            
            # 风险控制模块
            risk_config = self.config.get('risk_control', {})
            self.risk_control = RiskControlModule(risk_config, logger=self.logger)
            
            # 执行模块
            exchange_config = self.config.get('exchange', {})
            exchange_config['paper_trading'] = True  # 强制使用模拟交易
            self.execution = LiveExecutionModule(exchange_config, logger=self.logger)
            
            # 监控模块
            self.monitor = MonitorModule(logger=self.logger)
            
            # 添加价格回调
            self.execution.add_price_callback(self._on_price_update)
            
            # 初始化策略
            self._init_strategies()
            
            self.logger.info("所有模块初始化完成")
            
        except Exception as e:
            self.logger.error(f"模块初始化失败: {e}")
            raise
    
    def _init_strategies(self):
        """初始化策略"""
        symbols = self.config.get_symbols()
        
        for symbol_config in symbols:
            symbol = symbol_config['symbol']
            params = symbol_config.get('strategy_params', {})
            
            # 创建策略实例
            strategy = self.strategy_manager.create_strategy(
                'TrendFollowing', 
                params, 
                logger=self.logger
            )
            
            self.strategy_manager.add_strategy(f"TrendFollowing_{symbol}", strategy)
            self.logger.info(f"为{symbol}创建策略: TrendFollowing")
            
            # 初始化信号时间记录
            self.last_signal_time[symbol] = datetime.now()
    
    async def _on_price_update(self, symbol: str, price: float, data: Dict):
        """价格更新回调"""
        try:
            # 更新最新价格
            self.last_prices[symbol] = price
            
            # 更新价格数据缓存
            if symbol not in self.price_data:
                self.price_data[symbol] = []
            
            # 添加价格数据点
            price_point = {
                'timestamp': datetime.now(),
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': float(data.get('v', 0))  # 24h成交量
            }
            
            self.price_data[symbol].append(price_point)
            
            # 保持最近1000个数据点
            if len(self.price_data[symbol]) > 1000:
                self.price_data[symbol] = self.price_data[symbol][-1000:]
            
            # 检查是否需要生成交易信号
            await self._check_trading_signals(symbol)
            
        except Exception as e:
            self.logger.error(f"价格更新处理错误: {e}")
    
    async def _check_trading_signals(self, symbol: str):
        """检查交易信号"""
        try:
            # 限制信号频率（最少间隔5分钟）
            now = datetime.now()
            if symbol in self.last_signal_time:
                time_diff = now - self.last_signal_time[symbol]
                if time_diff.total_seconds() < 300:  # 5分钟
                    return
            
            # 需要足够的历史数据
            if len(self.price_data[symbol]) < 100:
                return
            
            # 转换为DataFrame
            df = pd.DataFrame(self.price_data[symbol])
            df.set_index('timestamp', inplace=True)
            
            # 获取对应的策略
            strategy_name = f"TrendFollowing_{symbol}"
            strategy = self.strategy_manager.get_strategy(strategy_name)
            
            if not strategy:
                return
            
            # 生成交易信号
            signals = strategy.generate_signals(df)
            
            if len(signals) == 0:
                return
            
            # 获取最新信号
            latest_signal = signals.iloc[-1]
            
            if latest_signal['signal'] != 0:
                self.logger.info(f"收到交易信号: {symbol} {latest_signal['signal']}")
                
                # 执行交易
                await self._execute_signal(symbol, latest_signal)
                
                # 更新信号时间
                self.last_signal_time[symbol] = now
                
        except Exception as e:
            self.logger.error(f"信号检查错误: {e}")
    
    async def _execute_signal(self, symbol: str, signal: pd.Series):
        """执行交易信号"""
        try:
            signal_value = signal['signal']
            current_price = self.last_prices.get(symbol, 0)
            
            if current_price == 0:
                self.logger.warning(f"无法获取{symbol}当前价格")
                return
            
            # 获取当前持仓
            positions = self.execution.get_positions()
            current_position = positions.get(symbol, {}).get('size', 0)
            
            # 计算交易数量
            balance = self.execution.get_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # 使用5%的资金进行交易
            trade_amount_usdt = usdt_balance * 0.05
            trade_amount = trade_amount_usdt / current_price
            
            # 风险检查
            can_trade, reason, adjusted_amount = self.risk_control.check_position_size(
                symbol, trade_amount, current_price
            )
            
            if not can_trade:
                self.logger.warning(f"风险检查未通过: {reason}")
                return
            
            # 执行交易
            if signal_value > 0 and current_position <= 0:
                # 买入信号
                order = await self.execution.place_order(
                    symbol=symbol,
                    side='buy',
                    amount=adjusted_amount,
                    order_type='market'
                )
                
                if order:
                    self.logger.info(f"买入订单执行成功: {symbol} {adjusted_amount}")
                    
            elif signal_value < 0 and current_position > 0:
                # 卖出信号
                order = await self.execution.place_order(
                    symbol=symbol,
                    side='sell',
                    amount=min(adjusted_amount, current_position),
                    order_type='market'
                )
                
                if order:
                    self.logger.info(f"卖出订单执行成功: {symbol} {adjusted_amount}")
            
        except Exception as e:
            self.logger.error(f"信号执行错误: {e}")
    
    async def start(self):
        """启动交易系统"""
        try:
            self.running = True
            self.logger.info("交易系统启动中...")
            
            # 获取交易币种
            symbols = [s['symbol'] for s in self.config.get_symbols()]
            self.logger.info(f"监控币种: {symbols}")
            
            # 启动价格流
            price_task = asyncio.create_task(
                self.execution.start_price_stream(symbols)
            )
            
            # 启动监控任务
            monitor_task = asyncio.create_task(self._monitor_loop())
            
            # 启动状态报告任务
            report_task = asyncio.create_task(self._report_loop())
            
            self.logger.info("✅ 交易系统已启动，等待价格数据...")
            
            # 等待任务完成
            await asyncio.gather(price_task, monitor_task, report_task)
            
        except Exception as e:
            self.logger.error(f"交易系统启动失败: {e}")
            raise
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 更新持仓盈亏
                await self._update_unrealized_pnl()
                
                # 检查风险控制
                await self._check_risk_control()
                
                # 等待30秒
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(10)
    
    async def _report_loop(self):
        """状态报告循环"""
        while self.running:
            try:
                # 每5分钟输出一次状态报告
                await self._print_status_report()
                await asyncio.sleep(300)  # 5分钟
                
            except Exception as e:
                self.logger.error(f"报告循环错误: {e}")
                await asyncio.sleep(60)
    
    async def _update_unrealized_pnl(self):
        """更新未实现盈亏"""
        try:
            positions = self.execution.get_positions()
            
            for symbol, position in positions.items():
                if position['size'] > 0:
                    current_price = self.last_prices.get(symbol, 0)
                    if current_price > 0:
                        unrealized_pnl = (current_price - position['entry_price']) * position['size']
                        position['unrealized_pnl'] = unrealized_pnl
                        
        except Exception as e:
            self.logger.error(f"更新盈亏失败: {e}")
    
    async def _check_risk_control(self):
        """检查风险控制"""
        try:
            positions = self.execution.get_positions()
            
            for symbol, position in positions.items():
                if position['size'] > 0:
                    current_price = self.last_prices.get(symbol, 0)
                    if current_price > 0:
                        # 检查止损
                        pnl_ratio = (current_price - position['entry_price']) / position['entry_price']
                        
                        stop_loss = self.config.get('risk_control.stop_loss', 0.02)
                        if pnl_ratio <= -stop_loss:
                            self.logger.warning(f"触发止损: {symbol} {pnl_ratio:.2%}")
                            await self.execution.place_order(symbol, 'sell', position['size'])
                        
                        # 检查止盈
                        take_profit = self.config.get('risk_control.take_profit', 0.04)
                        if pnl_ratio >= take_profit:
                            self.logger.info(f"触发止盈: {symbol} {pnl_ratio:.2%}")
                            await self.execution.place_order(symbol, 'sell', position['size'])
                            
        except Exception as e:
            self.logger.error(f"风险检查失败: {e}")
    
    async def _print_status_report(self):
        """打印状态报告"""
        try:
            print("\n" + "=" * 80)
            print(f"📊 交易系统状态报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            # 账户余额
            balance = self.execution.get_balance()
            print("💰 账户余额:")
            for currency, info in balance.items():
                if info['total'] > 0:
                    print(f"   {currency}: {info['free']:.4f} (可用) / {info['total']:.4f} (总计)")
            
            # 当前价格
            print("\n📈 当前价格:")
            for symbol, price in self.last_prices.items():
                print(f"   {symbol}: ${price:.2f}")
            
            # 持仓信息
            positions = self.execution.get_positions()
            print("\n📋 持仓信息:")
            if positions:
                for symbol, position in positions.items():
                    if position['size'] > 0:
                        current_price = self.last_prices.get(symbol, 0)
                        pnl = position.get('unrealized_pnl', 0)
                        pnl_pct = (pnl / (position['entry_price'] * position['size'])) * 100 if position['size'] > 0 else 0
                        
                        print(f"   {symbol}: {position['size']:.6f} @ ${position['entry_price']:.2f}")
                        print(f"     当前价格: ${current_price:.2f}")
                        print(f"     未实现盈亏: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            else:
                print("   无持仓")
            
            # 交易统计
            stats = self.execution.get_trade_stats()
            print("\n📊 交易统计:")
            print(f"   总交易次数: {stats['total_trades']}")
            print(f"   成功交易: {stats['successful_trades']}")
            print(f"   失败交易: {stats['failed_trades']}")
            print(f"   总交易量: ${stats['total_volume']:.2f}")
            print(f"   总手续费: ${stats['total_commission']:.2f}")
            
            print("=" * 80)
            
        except Exception as e:
            self.logger.error(f"状态报告错误: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到退出信号: {signum}")
        self.running = False
    
    async def stop(self):
        """停止交易系统"""
        self.logger.info("正在停止交易系统...")
        self.running = False
        
        # 平仓所有持仓
        await self.execution.close_all_positions()
        
        # 停止执行模块
        self.execution.stop()
        
        self.logger.info("交易系统已停止")

async def main():
    """主函数"""
    try:
        # 创建交易系统
        trading_system = LiveTradingSystem()
        
        # 启动系统
        await trading_system.start()
        
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
    except Exception as e:
        print(f"系统错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'trading_system' in locals():
            await trading_system.stop()

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
