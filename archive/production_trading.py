#!/usr/bin/env python3
"""
生产环境交易系统
支持实盘交易、完整监控和报警功能
"""

import asyncio
import signal
import sys
import os
import psutil
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils import ConfigLoader
from modules.log_module import LogModule
from modules.strategy_module import StrategyManager
from modules.risk_control_module import RiskControlModule
from modules.live_execution_module import LiveExecutionModule
from modules.data_module import DataModule
from modules.monitor_module import MonitorModule
from modules.notification_module import NotificationManager, AlertManager, ReportManager

class ProductionTradingSystem:
    """生产环境交易系统"""
    
    def __init__(self, config_path: str = "config/production.yaml"):
        # 加载配置
        self.config = ConfigLoader(config_path)
        
        # 初始化日志
        self.logger = LogModule()
        self.logger.info("=" * 80)
        self.logger.info("🚀 启动生产环境交易系统")
        self.logger.info("=" * 80)
        
        # 系统状态
        self.running = False
        self.start_time = datetime.now()
        self.last_health_check = datetime.now()
        self.restart_count = 0
        self.max_restart_attempts = self.config.get('system.max_restart_attempts', 5)
        
        # 性能监控
        self.system_stats = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'network_io': 0
        }
        
        # 交易统计
        self.daily_stats = {
            'trades_today': 0,
            'daily_pnl': 0,
            'daily_return': 0,
            'max_drawdown_today': 0,
            'last_reset_date': datetime.now().date()
        }
        
        # 初始化模块
        self._init_modules()
        
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
            # 生产环境默认关闭模拟交易
            exchange_config['paper_trading'] = False
            self.execution = LiveExecutionModule(exchange_config, logger=self.logger)
            
            # 监控模块
            self.monitor = MonitorModule(logger=self.logger)
            
            # 通知模块
            notification_config = self.config.get('notifications', {})
            self.notification_manager = NotificationManager(notification_config, self.logger)
            
            # 报警模块
            monitoring_config = self.config.get('monitoring', {})
            self.alert_manager = AlertManager(monitoring_config, self.notification_manager, self.logger)
            
            # 报告模块
            self.report_manager = ReportManager(self.notification_manager, self.logger)
            
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
        
        # 检查是否启用多策略
        multi_strategy_config = self.config.get('strategy.multi_strategy', {})
        if multi_strategy_config.get('enabled', False):
            # 多策略模式
            strategies_config = multi_strategy_config.get('strategies', [])
            
            for strategy_config in strategies_config:
                if not strategy_config.get('enabled', True):
                    continue
                
                strategy_name = strategy_config['name']
                weight = strategy_config.get('weight', 1.0)
                
                for symbol_config in symbols:
                    symbol = symbol_config['symbol']
                    params = symbol_config.get('strategy_params', {})
                    params['weight'] = weight
                    
                    # 创建策略实例
                    try:
                        strategy = self.strategy_manager.create_strategy(strategy_name, params)
                        strategy_key = f"{strategy_name}_{symbol}"
                        self.strategy_manager.add_strategy(strategy_key, strategy)
                        self.logger.info(f"创建策略: {strategy_key} (权重: {weight})")
                    except Exception as e:
                        self.logger.error(f"创建策略失败 {strategy_name}: {e}")
        else:
            # 单策略模式
            strategy_name = self.config.get('strategy.name', 'TrendFollowing')
            
            for symbol_config in symbols:
                symbol = symbol_config['symbol']
                params = symbol_config.get('strategy_params', {})
                
                # 创建策略实例
                strategy = self.strategy_manager.create_strategy(strategy_name, params)
                strategy_key = f"{strategy_name}_{symbol}"
                self.strategy_manager.add_strategy(strategy_key, strategy)
                self.logger.info(f"创建策略: {strategy_key}")
    
    async def _on_price_update(self, symbol: str, price: float, data: Dict):
        """价格更新回调"""
        try:
            # 更新系统状态
            await self._update_system_status()
            
            # 检查交易信号
            await self._check_trading_signals(symbol, price, data)
            
            # 检查风险控制
            await self._check_risk_management()
            
            # 检查报警条件
            system_status = await self._get_system_status()
            self.alert_manager.check_alerts(system_status)
            
        except Exception as e:
            self.logger.error(f"价格更新处理错误: {e}")
    
    async def _check_trading_signals(self, symbol: str, price: float, data: Dict):
        """检查交易信号"""
        try:
            # 获取历史数据用于策略计算
            # 这里简化处理，实际应该维护价格数据缓存
            
            # 检查日交易次数限制
            max_trades_per_day = self.config.get('risk_control.max_trades_per_day', 10)
            if self.daily_stats['trades_today'] >= max_trades_per_day:
                return
            
            # 获取相关策略
            relevant_strategies = [
                (name, strategy) for name, strategy in self.strategy_manager.strategies.items()
                if symbol in name
            ]
            
            if not relevant_strategies:
                return
            
            # 多策略信号聚合
            total_signal = 0
            total_weight = 0
            
            for strategy_name, strategy in relevant_strategies:
                try:
                    # 这里需要实际的历史数据，暂时跳过信号生成
                    # signal_strength = strategy.get_signal_strength(historical_data)
                    # weight = getattr(strategy, 'weight', 1.0)
                    # total_signal += signal_strength * weight
                    # total_weight += weight
                    pass
                except Exception as e:
                    self.logger.error(f"策略{strategy_name}信号生成失败: {e}")
            
            # 执行交易逻辑
            if total_weight > 0:
                avg_signal = total_signal / total_weight
                
                if abs(avg_signal) > 0.5:  # 信号强度阈值
                    await self._execute_trade_signal(symbol, avg_signal, price)
            
        except Exception as e:
            self.logger.error(f"交易信号检查失败: {e}")
    
    async def _execute_trade_signal(self, symbol: str, signal: float, price: float):
        """执行交易信号"""
        try:
            # 确定交易方向和数量
            side = 'buy' if signal > 0 else 'sell'
            
            # 计算交易数量
            balance = self.execution.get_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # 风险控制检查
            max_trade_amount = self.config.get('risk_control.max_trade_amount', 100)
            min_trade_amount = self.config.get('risk_control.min_trade_amount', 10)
            
            trade_amount_usdt = min(max_trade_amount, usdt_balance * 0.1)  # 最多使用10%资金
            
            if trade_amount_usdt < min_trade_amount:
                self.logger.warning(f"交易金额不足最小限制: {trade_amount_usdt}")
                return
            
            trade_amount = trade_amount_usdt / price
            
            # 风险检查
            can_trade, reason, adjusted_amount = self.risk_control.check_position_size(
                symbol, trade_amount, price
            )
            
            if not can_trade:
                self.logger.warning(f"风险检查未通过: {reason}")
                return
            
            # 执行交易
            order = await self.execution.place_order(
                symbol=symbol,
                side=side,
                amount=adjusted_amount,
                order_type='market'
            )
            
            if order:
                # 更新统计
                self.daily_stats['trades_today'] += 1
                
                # 发送交易通知
                trade_info = {
                    'symbol': symbol,
                    'side': side,
                    'amount': adjusted_amount,
                    'price': price
                }
                self.notification_manager.send_trade_notification(trade_info)
                
                self.logger.info(f"交易执行成功: {symbol} {side} {adjusted_amount}")
            
        except Exception as e:
            self.logger.error(f"交易执行失败: {e}")
    
    async def _check_risk_management(self):
        """检查风险管理"""
        try:
            positions = self.execution.get_positions()
            
            for symbol, position in positions.items():
                if position['size'] == 0:
                    continue
                
                current_price = self.execution.get_current_price(symbol)
                if current_price == 0:
                    continue
                
                # 更新未实现盈亏
                position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
                pnl_ratio = position['unrealized_pnl'] / (position['entry_price'] * abs(position['size']))
                
                # 检查止损
                stop_loss = self.config.get('risk_control.stop_loss', 0.02)
                if pnl_ratio <= -stop_loss:
                    self.logger.warning(f"触发止损: {symbol} {pnl_ratio:.2%}")
                    await self.execution.place_order(symbol, 'sell', abs(position['size']))
                
                # 检查止盈
                take_profit = self.config.get('risk_control.take_profit', 0.04)
                if pnl_ratio >= take_profit:
                    self.logger.info(f"触发止盈: {symbol} {pnl_ratio:.2%}")
                    await self.execution.place_order(symbol, 'sell', abs(position['size']))
                
                # 检查紧急止损
                emergency_stop = self.config.get('risk_control.emergency_stop_loss', 0.05)
                if pnl_ratio <= -emergency_stop:
                    self.logger.error(f"触发紧急止损: {symbol} {pnl_ratio:.2%}")
                    await self.execution.place_order(symbol, 'sell', abs(position['size']))
                    
                    # 发送紧急通知
                    self.notification_manager.send_alert_notification('emergency_stop', {
                        'symbol': symbol,
                        'pnl_ratio': pnl_ratio,
                        'threshold': emergency_stop
                    })
            
        except Exception as e:
            self.logger.error(f"风险管理检查失败: {e}")
    
    async def _update_system_status(self):
        """更新系统状态"""
        try:
            # 更新性能统计
            self.system_stats['cpu_usage'] = psutil.cpu_percent()
            self.system_stats['memory_usage'] = psutil.virtual_memory().percent
            self.system_stats['disk_usage'] = psutil.disk_usage('/').percent
            
            # 重置日统计（如果是新的一天）
            current_date = datetime.now().date()
            if current_date != self.daily_stats['last_reset_date']:
                self.daily_stats = {
                    'trades_today': 0,
                    'daily_pnl': 0,
                    'daily_return': 0,
                    'max_drawdown_today': 0,
                    'last_reset_date': current_date
                }
            
        except Exception as e:
            self.logger.error(f"系统状态更新失败: {e}")
    
    async def _get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            balance = self.execution.get_balance()
            positions = self.execution.get_positions()
            trade_stats = self.execution.get_trade_stats()
            
            # 计算总资产
            total_balance = 0
            available_balance = balance.get('USDT', {}).get('free', 0)
            position_value = 0
            
            for symbol, position in positions.items():
                if position['size'] > 0:
                    current_price = self.execution.get_current_price(symbol)
                    position_value += position['size'] * current_price
            
            total_balance = available_balance + position_value
            
            # 计算今日收益率
            initial_capital = self.config.get('risk_control.initial_capital', 1000)
            daily_return = (total_balance - initial_capital) / initial_capital
            
            return {
                'uptime': (datetime.now() - self.start_time).total_seconds(),
                'total_balance': total_balance,
                'available_balance': available_balance,
                'position_value': position_value,
                'daily_return': daily_return,
                'trade_count': self.daily_stats['trades_today'],
                'max_drawdown': self.daily_stats['max_drawdown_today'],
                'positions': positions,
                'system_stats': self.system_stats,
                'has_error': False,
                'last_error': None
            }
            
        except Exception as e:
            self.logger.error(f"获取系统状态失败: {e}")
            return {
                'has_error': True,
                'last_error': str(e)
            }
    
    async def _health_check(self):
        """健康检查"""
        try:
            current_time = datetime.now()
            
            # 检查系统资源
            cpu_threshold = self.config.get('system.performance_monitoring.cpu_threshold', 80)
            memory_threshold = self.config.get('system.performance_monitoring.memory_threshold', 80)
            
            if self.system_stats['cpu_usage'] > cpu_threshold:
                self.logger.warning(f"CPU使用率过高: {self.system_stats['cpu_usage']:.1f}%")
            
            if self.system_stats['memory_usage'] > memory_threshold:
                self.logger.warning(f"内存使用率过高: {self.system_stats['memory_usage']:.1f}%")
            
            # 检查交易所连接
            try:
                balance = self.execution.get_balance()
                if not balance:
                    self.logger.warning("无法获取账户余额，可能存在连接问题")
            except Exception as e:
                self.logger.error(f"交易所连接检查失败: {e}")
            
            self.last_health_check = current_time
            
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 健康检查
                await self._health_check()
                
                # 更新系统状态
                await self._update_system_status()
                
                # 检查是否需要发送日报
                system_status = await self._get_system_status()
                self.report_manager.send_daily_report_if_needed(system_status)
                
                # 等待下次检查
                update_interval = self.config.get('monitoring.update_interval', 30)
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """启动交易系统"""
        try:
            self.running = True
            self.logger.info("生产环境交易系统启动中...")
            
            # 发送启动通知
            self.notification_manager.send_notification(
                "生产环境交易系统已启动", 
                "系统启动", 
                priority="high"
            )
            
            # 获取交易币种
            symbols = [s['symbol'] for s in self.config.get_symbols()]
            self.logger.info(f"监控币种: {symbols}")
            
            # 启动价格流
            price_task = asyncio.create_task(
                self.execution.start_price_stream(symbols)
            )
            
            # 启动监控任务
            monitor_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("✅ 生产环境交易系统已启动")
            
            # 等待任务完成
            await asyncio.gather(price_task, monitor_task)
            
        except Exception as e:
            self.logger.error(f"交易系统启动失败: {e}")
            
            # 发送错误通知
            self.notification_manager.send_alert_notification('system_error', {
                'error': str(e)
            })
            
            raise
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到退出信号: {signum}")
        self.running = False
    
    async def stop(self):
        """停止交易系统"""
        self.logger.info("正在停止生产环境交易系统...")
        self.running = False
        
        try:
            # 平仓所有持仓（可选）
            # await self.execution.close_all_positions()
            
            # 停止执行模块
            self.execution.stop()
            
            # 发送停止通知
            self.notification_manager.send_notification(
                "生产环境交易系统已停止", 
                "系统停止", 
                priority="high"
            )
            
            self.logger.info("生产环境交易系统已停止")
            
        except Exception as e:
            self.logger.error(f"系统停止过程中出现错误: {e}")

async def main():
    """主函数"""
    try:
        # 检查配置文件
        if not os.path.exists("config/production.yaml"):
            print("❌ 生产环境配置文件不存在: config/production.yaml")
            print("💡 请先创建生产环境配置文件")
            return
        
        # 检查环境变量
        if not os.getenv('BINANCE_API_KEY') or not os.getenv('BINANCE_SECRET'):
            print("❌ 请设置环境变量 BINANCE_API_KEY 和 BINANCE_SECRET")
            return
        
        # 确认启动
        print("⚠️  您即将启动生产环境交易系统")
        print("⚠️  这将使用真实资金进行交易")
        print("⚠️  请确保您已经充分测试并了解风险")
        
        confirm = input("确认启动生产环境交易系统? (yes/no): ")
        if confirm.lower() != 'yes':
            print("取消启动")
            return
        
        # 创建交易系统
        trading_system = ProductionTradingSystem()
        
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
