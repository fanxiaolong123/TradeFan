"""
交易执行器基类
抽象交易执行流程，包括信号生成、风险检查、订单执行
统一管理交易生命周期
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from enum import Enum

from .api_client import APIClient
from .config_manager import ConfigManager
from .logger import LoggerManager


class TradingState(Enum):
    """交易状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class Position:
    """持仓信息类"""
    
    def __init__(self, symbol: str, side: str, size: float, entry_price: float, 
                 entry_time: datetime, strategy: str = None):
        self.symbol = symbol
        self.side = side  # 'long' or 'short'
        self.size = size
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.strategy = strategy
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
        self.current_price = entry_price
        
    def update_price(self, current_price: float):
        """更新当前价格和未实现盈亏"""
        self.current_price = current_price
        if self.side == 'long':
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
    
    def get_pnl_ratio(self) -> float:
        """获取盈亏比例"""
        if self.entry_price == 0:
            return 0.0
        return self.unrealized_pnl / (self.entry_price * self.size)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'pnl_ratio': self.get_pnl_ratio(),
            'strategy': self.strategy
        }


class TradingExecutor(ABC):
    """交易执行器抽象基类"""
    
    def __init__(self, config_manager: ConfigManager, logger_manager: LoggerManager,
                 config_name: str = "trading"):
        """
        初始化交易执行器
        
        Args:
            config_manager: 配置管理器
            logger_manager: 日志管理器
            config_name: 配置名称
        """
        self.config_manager = config_manager
        self.logger_manager = logger_manager
        self.config_name = config_name
        
        # 加载配置
        self.config = self.config_manager.load_config(config_name)
        
        # 创建日志器
        self.logger = self.logger_manager.get_trading_logger(self.__class__.__name__)
        self.api_logger = self.logger_manager.get_api_logger()
        self.risk_logger = self.logger_manager.get_risk_logger()
        
        # 初始化API客户端
        self.api_client = self._init_api_client()
        
        # 交易状态
        self.state = TradingState.STOPPED
        self.start_time = None
        self.last_update_time = None
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Dict] = {}
        
        # 统计信息
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'max_drawdown': 0.0,
            'consecutive_losses': 0,
            'last_trade_time': None
        }
        
        # 风险控制
        self.risk_limits = self.config.get('risk_management', {})
        self.daily_loss_limit = self.risk_limits.get('max_daily_loss', 0.02)
        self.position_risk_limit = self.risk_limits.get('max_position_risk', 0.01)
        
        self.logger.info(f"🚀 交易执行器初始化完成: {self.__class__.__name__}")
    
    def _init_api_client(self) -> APIClient:
        """初始化API客户端"""
        api_config = self.config['api']
        
        return APIClient(
            exchange=api_config['exchange'],
            api_key=api_config['api_key'],
            api_secret=api_config['api_secret'],
            base_url=api_config['base_url'],
            testnet=api_config.get('testnet', True),
            logger=self.api_logger
        )
    
    @abstractmethod
    async def generate_signals(self, symbol: str) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            symbol: 交易对
            
        Returns:
            信号字典 {'signal': 1/-1/0, 'strength': 0-1, 'reason': str}
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        获取市场数据
        
        Args:
            symbol: 交易对
            timeframe: 时间框架
            limit: 数据条数
            
        Returns:
            市场数据DataFrame
        """
        pass
    
    async def start_trading(self):
        """启动交易"""
        if self.state != TradingState.STOPPED:
            self.logger.warning("⚠️ 交易系统已在运行中")
            return
        
        self.logger.info("🚀 启动交易系统...")
        self.state = TradingState.STARTING
        
        try:
            # 验证API连接
            if not self.api_client.test_connectivity():
                raise Exception("API连接测试失败")
            
            # 验证账户权限
            account_info = self.api_client.get_account_info()
            self.logger.info(f"✅ 账户验证成功: {account_info.get('accountType', 'Unknown')}")
            
            # 初始化持仓
            await self._sync_positions()
            
            # 启动主循环
            self.state = TradingState.RUNNING
            self.start_time = datetime.now()
            
            self.logger.info("✅ 交易系统启动成功")
            
            # 开始交易循环
            await self._trading_loop()
            
        except Exception as e:
            self.state = TradingState.ERROR
            self.logger_manager.log_exception(self.logger, e, "启动交易系统")
            raise
    
    async def stop_trading(self):
        """停止交易"""
        if self.state == TradingState.STOPPED:
            return
        
        self.logger.info("🛑 停止交易系统...")
        self.state = TradingState.STOPPING
        
        try:
            # 取消所有未成交订单
            await self._cancel_all_orders()
            
            # 记录最终统计
            self._log_final_stats()
            
            self.state = TradingState.STOPPED
            self.logger.info("✅ 交易系统已停止")
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, "停止交易系统")
    
    async def _trading_loop(self):
        """主交易循环"""
        symbols = self.config['trading']['symbols']
        update_interval = self.config['trading'].get('update_interval', 60)  # 秒
        
        while self.state == TradingState.RUNNING:
            try:
                loop_start_time = time.time()
                
                # 更新市场数据和持仓
                await self._update_positions()
                
                # 风险检查
                if not self._check_risk_limits():
                    self.logger.warning("⚠️ 触发风险限制，暂停交易")
                    self.state = TradingState.PAUSED
                    await asyncio.sleep(300)  # 暂停5分钟
                    continue
                
                # 处理每个交易对
                for symbol in symbols:
                    if self.state != TradingState.RUNNING:
                        break
                    
                    try:
                        await self._process_symbol(symbol)
                    except Exception as e:
                        self.logger_manager.log_exception(self.logger, e, f"处理交易对 {symbol}")
                
                # 更新统计信息
                self._update_stats()
                
                # 计算循环耗时
                loop_time = time.time() - loop_start_time
                self.logger.debug(f"⏱️ 交易循环耗时: {loop_time:.2f}秒")
                
                # 等待下次更新
                sleep_time = max(0, update_interval - loop_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                self.last_update_time = datetime.now()
                
            except Exception as e:
                self.logger_manager.log_exception(self.logger, e, "交易主循环")
                await asyncio.sleep(60)  # 出错后等待1分钟
    
    async def _process_symbol(self, symbol: str):
        """
        处理单个交易对
        
        Args:
            symbol: 交易对
        """
        # 生成交易信号
        signal_data = await self.generate_signals(symbol)
        signal = signal_data.get('signal', 0)
        
        if signal == 0:
            return  # 无信号
        
        # 记录信号
        self.logger_manager.log_trade_event(
            self.logger, 'signal', symbol, signal_data
        )
        
        # 检查是否可以开仓
        if not self._can_open_position(symbol, signal):
            return
        
        # 计算仓位大小
        position_size = self._calculate_position_size(symbol, signal)
        if position_size <= 0:
            return
        
        # 执行交易
        await self._execute_trade(symbol, signal, position_size, signal_data)
    
    def _can_open_position(self, symbol: str, signal: int) -> bool:
        """
        检查是否可以开仓
        
        Args:
            symbol: 交易对
            signal: 交易信号
            
        Returns:
            是否可以开仓
        """
        # 检查是否已有持仓
        if symbol in self.positions:
            current_position = self.positions[symbol]
            # 如果信号方向与当前持仓相同，不重复开仓
            if (signal > 0 and current_position.side == 'long') or \
               (signal < 0 and current_position.side == 'short'):
                return False
        
        # 检查最大持仓数量
        max_positions = self.config['trading'].get('max_positions', 5)
        if len(self.positions) >= max_positions:
            self.logger.warning(f"⚠️ 已达到最大持仓数量: {max_positions}")
            return False
        
        # 检查连续亏损限制
        max_consecutive_losses = self.risk_limits.get('max_consecutive_losses', 5)
        if self.stats['consecutive_losses'] >= max_consecutive_losses:
            self.logger.warning(f"⚠️ 连续亏损次数过多: {self.stats['consecutive_losses']}")
            return False
        
        return True
    
    def _calculate_position_size(self, symbol: str, signal: int) -> float:
        """
        计算仓位大小
        
        Args:
            symbol: 交易对
            signal: 交易信号
            
        Returns:
            仓位大小
        """
        try:
            # 获取账户余额
            base_currency = self.config['trading']['base_currency']
            balance_info = self.api_client.get_balance(base_currency)
            available_balance = balance_info.get('free', 0)
            
            # 获取当前价格
            ticker = self.api_client.get_ticker(symbol)
            current_price = float(ticker['lastPrice'])
            
            # 计算仓位大小
            position_ratio = self.config['trading'].get('position_size_ratio', 0.1)
            max_position_value = available_balance * position_ratio
            
            # 考虑风险限制
            risk_adjusted_value = min(
                max_position_value,
                available_balance * self.position_risk_limit
            )
            
            position_size = risk_adjusted_value / current_price
            
            # 获取交易对信息进行精度调整
            exchange_info = self.api_client.get_exchange_info(symbol)
            # 这里需要根据具体交易所调整精度逻辑
            
            return round(position_size, 6)  # 临时使用6位小数
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, f"计算仓位大小 {symbol}")
            return 0.0
    
    async def _execute_trade(self, symbol: str, signal: int, position_size: float, 
                           signal_data: Dict[str, Any]):
        """
        执行交易
        
        Args:
            symbol: 交易对
            signal: 交易信号
            position_size: 仓位大小
            signal_data: 信号数据
        """
        try:
            side = 'BUY' if signal > 0 else 'SELL'
            
            # 如果已有反向持仓，先平仓
            if symbol in self.positions:
                await self._close_position(symbol, "信号反转")
            
            # 下市价单
            order_result = self.api_client.place_order(
                symbol=symbol,
                side=side,
                order_type='MARKET',
                quantity=position_size
            )
            
            # 记录订单
            order_id = order_result.get('orderId')
            self.orders[order_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': position_size,
                'type': 'MARKET',
                'status': 'NEW',
                'timestamp': datetime.now(),
                'signal_data': signal_data
            }
            
            self.logger_manager.log_trade_event(
                self.logger, 'order', symbol, {
                    'order_id': order_id,
                    'side': side,
                    'quantity': position_size,
                    'type': 'MARKET'
                }
            )
            
            # 等待订单成交
            await self._wait_for_order_fill(order_id)
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, f"执行交易 {symbol}")
    
    async def _wait_for_order_fill(self, order_id: str, timeout: int = 30):
        """
        等待订单成交
        
        Args:
            order_id: 订单ID
            timeout: 超时时间（秒）
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                order_info = self.orders.get(order_id, {})
                symbol = order_info.get('symbol')
                
                if not symbol:
                    break
                
                # 查询订单状态
                order_status = self.api_client.get_order_status(symbol, order_id)
                status = order_status.get('status')
                
                if status == 'FILLED':
                    # 订单已成交，创建持仓
                    await self._create_position_from_order(order_id, order_status)
                    break
                elif status in ['CANCELED', 'REJECTED', 'EXPIRED']:
                    # 订单失败
                    self.logger.error(f"❌ 订单失败: {order_id} - {status}")
                    break
                
                await asyncio.sleep(1)  # 等待1秒后重试
                
            except Exception as e:
                self.logger_manager.log_exception(self.logger, e, f"等待订单成交 {order_id}")
                break
    
    async def _create_position_from_order(self, order_id: str, order_status: Dict[str, Any]):
        """
        从成交订单创建持仓
        
        Args:
            order_id: 订单ID
            order_status: 订单状态信息
        """
        try:
            order_info = self.orders[order_id]
            symbol = order_info['symbol']
            side = 'long' if order_info['side'] == 'BUY' else 'short'
            
            # 获取成交信息
            executed_qty = float(order_status.get('executedQty', 0))
            avg_price = float(order_status.get('avgPrice', 0))
            
            if executed_qty > 0 and avg_price > 0:
                # 创建持仓
                position = Position(
                    symbol=symbol,
                    side=side,
                    size=executed_qty,
                    entry_price=avg_price,
                    entry_time=datetime.now(),
                    strategy=self.__class__.__name__
                )
                
                self.positions[symbol] = position
                
                # 记录成交事件
                self.logger_manager.log_trade_event(
                    self.logger, 'fill', symbol, {
                        'order_id': order_id,
                        'side': order_info['side'],
                        'quantity': executed_qty,
                        'price': avg_price,
                        'position_side': side
                    }
                )
                
                # 更新统计
                self.stats['total_trades'] += 1
                self.stats['last_trade_time'] = datetime.now()
                
                self.logger.info(f"✅ 建仓成功: {symbol} {side} {executed_qty} @ {avg_price}")
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, f"创建持仓 {order_id}")
    
    async def _close_position(self, symbol: str, reason: str = "手动平仓"):
        """
        平仓
        
        Args:
            symbol: 交易对
            reason: 平仓原因
        """
        if symbol not in self.positions:
            return
        
        try:
            position = self.positions[symbol]
            
            # 确定平仓方向
            close_side = 'SELL' if position.side == 'long' else 'BUY'
            
            # 下市价平仓单
            order_result = self.api_client.place_order(
                symbol=symbol,
                side=close_side,
                order_type='MARKET',
                quantity=position.size
            )
            
            order_id = order_result.get('orderId')
            
            self.logger_manager.log_trade_event(
                self.logger, 'order', symbol, {
                    'order_id': order_id,
                    'side': close_side,
                    'quantity': position.size,
                    'type': 'MARKET',
                    'reason': reason
                }
            )
            
            # 等待成交并更新统计
            await self._wait_for_position_close(order_id, symbol)
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, f"平仓 {symbol}")
    
    async def _wait_for_position_close(self, order_id: str, symbol: str):
        """等待平仓订单成交"""
        start_time = time.time()
        
        while time.time() - start_time < 30:  # 30秒超时
            try:
                order_status = self.api_client.get_order_status(symbol, order_id)
                status = order_status.get('status')
                
                if status == 'FILLED':
                    # 计算盈亏
                    position = self.positions[symbol]
                    executed_qty = float(order_status.get('executedQty', 0))
                    avg_price = float(order_status.get('avgPrice', 0))
                    
                    if position.side == 'long':
                        pnl = (avg_price - position.entry_price) * executed_qty
                    else:
                        pnl = (position.entry_price - avg_price) * executed_qty
                    
                    # 更新统计
                    self.stats['total_pnl'] += pnl
                    self.stats['daily_pnl'] += pnl
                    
                    if pnl > 0:
                        self.stats['winning_trades'] += 1
                        self.stats['consecutive_losses'] = 0
                    else:
                        self.stats['losing_trades'] += 1
                        self.stats['consecutive_losses'] += 1
                    
                    # 记录平仓事件
                    self.logger_manager.log_trade_event(
                        self.logger, 'fill', symbol, {
                            'order_id': order_id,
                            'side': 'CLOSE',
                            'quantity': executed_qty,
                            'price': avg_price,
                            'pnl': pnl,
                            'pnl_ratio': pnl / (position.entry_price * position.size)
                        }
                    )
                    
                    # 移除持仓
                    del self.positions[symbol]
                    
                    self.logger.info(f"✅ 平仓成功: {symbol} 盈亏: {pnl:.4f}")
                    break
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger_manager.log_exception(self.logger, e, f"等待平仓成交 {symbol}")
                break
    
    async def _sync_positions(self):
        """同步持仓信息"""
        try:
            # 这里可以从交易所获取当前持仓
            # 暂时使用空实现
            self.logger.info("📊 持仓同步完成")
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, "同步持仓")
    
    async def _update_positions(self):
        """更新持仓信息"""
        for symbol, position in self.positions.items():
            try:
                # 获取当前价格
                ticker = self.api_client.get_ticker(symbol)
                current_price = float(ticker['lastPrice'])
                
                # 更新持仓价格和盈亏
                position.update_price(current_price)
                
                # 检查止损止盈
                await self._check_stop_conditions(symbol, position)
                
            except Exception as e:
                self.logger_manager.log_exception(self.logger, e, f"更新持仓 {symbol}")
    
    async def _check_stop_conditions(self, symbol: str, position: Position):
        """
        检查止损止盈条件
        
        Args:
            symbol: 交易对
            position: 持仓信息
        """
        pnl_ratio = position.get_pnl_ratio()
        
        # 止损检查
        stop_loss = self.risk_limits.get('stop_loss', 0.02)
        if pnl_ratio <= -stop_loss:
            await self._close_position(symbol, f"止损触发 (亏损{pnl_ratio:.2%})")
            return
        
        # 止盈检查
        take_profit = self.risk_limits.get('take_profit', 0.04)
        if pnl_ratio >= take_profit:
            await self._close_position(symbol, f"止盈触发 (盈利{pnl_ratio:.2%})")
            return
    
    def _check_risk_limits(self) -> bool:
        """检查风险限制"""
        # 检查日亏损限制
        if abs(self.stats['daily_pnl']) >= self.daily_loss_limit * self._get_account_balance():
            self.risk_logger.warning(f"⚠️ 触发日亏损限制: {self.stats['daily_pnl']}")
            return False
        
        # 检查连续亏损
        max_consecutive_losses = self.risk_limits.get('max_consecutive_losses', 5)
        if self.stats['consecutive_losses'] >= max_consecutive_losses:
            self.risk_logger.warning(f"⚠️ 连续亏损过多: {self.stats['consecutive_losses']}")
            return False
        
        return True
    
    def _get_account_balance(self) -> float:
        """获取账户余额"""
        try:
            base_currency = self.config['trading']['base_currency']
            balance_info = self.api_client.get_balance(base_currency)
            return balance_info.get('total', 0)
        except:
            return 10000  # 默认值
    
    async def _cancel_all_orders(self):
        """取消所有未成交订单"""
        try:
            open_orders = self.api_client.get_open_orders()
            
            for order in open_orders:
                order_id = order.get('orderId')
                symbol = order.get('symbol')
                
                if order_id and symbol:
                    self.api_client.cancel_order(symbol, order_id)
                    self.logger.info(f"❌ 取消订单: {order_id}")
            
        except Exception as e:
            self.logger_manager.log_exception(self.logger, e, "取消所有订单")
    
    def _update_stats(self):
        """更新统计信息"""
        # 计算胜率
        total_closed_trades = self.stats['winning_trades'] + self.stats['losing_trades']
        if total_closed_trades > 0:
            win_rate = self.stats['winning_trades'] / total_closed_trades
        else:
            win_rate = 0
        
        # 计算最大回撤
        # 这里需要更复杂的逻辑来跟踪历史净值
        
        # 记录统计信息
        if self.stats['total_trades'] % 10 == 0:  # 每10笔交易记录一次
            self.logger.info(f"📊 交易统计 - 总交易: {self.stats['total_trades']}, "
                           f"胜率: {win_rate:.2%}, 总盈亏: {self.stats['total_pnl']:.4f}")
    
    def _log_final_stats(self):
        """记录最终统计信息"""
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        final_stats = {
            'runtime': str(runtime),
            'total_trades': self.stats['total_trades'],
            'winning_trades': self.stats['winning_trades'],
            'losing_trades': self.stats['losing_trades'],
            'win_rate': self.stats['winning_trades'] / max(self.stats['winning_trades'] + self.stats['losing_trades'], 1),
            'total_pnl': self.stats['total_pnl'],
            'daily_pnl': self.stats['daily_pnl'],
            'open_positions': len(self.positions)
        }
        
        self.logger.info(f"📊 最终统计: {final_stats}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取交易系统状态"""
        return {
            'state': self.state.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
            'stats': self.stats.copy(),
            'config': self.config_name,
            'api_stats': self.api_client.get_statistics()
        }
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.state.value}, positions={len(self.positions)})"
    
    def __repr__(self):
        return self.__str__()
