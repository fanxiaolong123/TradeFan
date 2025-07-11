"""
执行模块
负责订单执行、模拟撮合等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import uuid
from .utils import Order, OrderType, OrderStatus

class ExecutionModule:
    """订单执行模块"""
    
    def __init__(self, config: Dict, data_module=None, logger=None):
        self.config = config
        self.data_module = data_module
        self.logger = logger
        
        # 执行参数
        self.commission_rate = config.get('backtest', {}).get('commission', 0.001)
        self.slippage = 0.0001  # 滑点
        
        # 订单管理
        self.pending_orders = {}  # order_id -> Order
        self.filled_orders = []
        self.cancelled_orders = []
        
        # 模拟撮合参数
        self.simulate_partial_fill = False
        self.simulate_rejection = False
        
        if self.logger:
            self.logger.info(f"执行模块初始化完成 - 手续费率: {self.commission_rate:.4f}")
    
    def create_order(self, symbol: str, side: str, amount: float, 
                    price: float = None, order_type: str = "market") -> Order:
        """
        创建订单
        
        Args:
            symbol: 交易对
            side: 买卖方向 (buy/sell)
            amount: 数量
            price: 价格 (市价单可为None)
            order_type: 订单类型 (market/limit)
            
        Returns:
            订单对象
        """
        try:
            # 获取当前价格（如果是市价单）
            if order_type == "market" or price is None:
                ticker = self._get_current_price(symbol)
                if ticker:
                    price = ticker['ask'] if side == OrderType.BUY else ticker['bid']
                else:
                    raise Exception(f"无法获取{symbol}当前价格")
            
            # 创建订单
            order = Order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                order_type=order_type
            )
            
            # 添加到待处理订单
            self.pending_orders[order.order_id] = order
            
            if self.logger:
                self.logger.info(f"创建订单: {symbol} {side.upper()} {amount:.6f} @ {price:.6f}")
            
            return order
            
        except Exception as e:
            error_msg = f"创建订单失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def execute_order(self, order: Order, current_price: float = None) -> bool:
        """
        执行订单
        
        Args:
            order: 订单对象
            current_price: 当前价格
            
        Returns:
            是否执行成功
        """
        try:
            if order.order_id not in self.pending_orders:
                if self.logger:
                    self.logger.warning(f"订单{order.order_id}不在待处理列表中")
                return False
            
            # 获取执行价格
            if current_price is None:
                ticker = self._get_current_price(order.symbol)
                if not ticker:
                    if self.logger:
                        self.logger.error(f"无法获取{order.symbol}当前价格")
                    return False
                current_price = ticker['ask'] if order.side == OrderType.BUY else ticker['bid']
            
            # 模拟滑点
            execution_price = self._apply_slippage(current_price, order.side)
            
            # 计算手续费
            commission = order.amount * execution_price * self.commission_rate
            
            # 执行订单
            order.fill(execution_price, order.amount, commission)
            
            # 从待处理订单中移除
            del self.pending_orders[order.order_id]
            
            # 添加到已成交订单
            self.filled_orders.append(order)
            
            if self.logger:
                self.logger.info(f"订单执行成功: {order.symbol} {order.side.upper()} "
                               f"{order.filled_amount:.6f} @ {order.filled_price:.6f} "
                               f"手续费: {commission:.6f}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"执行订单失败: {e}")
            order.status = OrderStatus.REJECTED
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            if order_id in self.pending_orders:
                order = self.pending_orders[order_id]
                order.cancel()
                del self.pending_orders[order_id]
                self.cancelled_orders.append(order)
                
                if self.logger:
                    self.logger.info(f"订单已取消: {order_id}")
                return True
            else:
                if self.logger:
                    self.logger.warning(f"订单{order_id}不存在或已处理")
                return False
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"取消订单失败: {e}")
            return False
    
    def simulate_market_order(self, symbol: str, side: str, amount: float, 
                            market_data: pd.DataFrame) -> Optional[Order]:
        """
        模拟市价单执行（用于回测）
        
        Args:
            symbol: 交易对
            side: 买卖方向
            amount: 数量
            market_data: 市场数据（当前K线）
            
        Returns:
            执行后的订单
        """
        try:
            if market_data.empty:
                return None
            
            # 使用当前K线的开盘价作为执行价格
            current_bar = market_data.iloc[-1]
            execution_price = current_bar['open']
            
            # 应用滑点
            execution_price = self._apply_slippage(execution_price, side)
            
            # 创建并执行订单
            order = Order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=execution_price,
                order_type="market"
            )
            
            # 计算手续费
            commission = amount * execution_price * self.commission_rate
            
            # 填充订单
            order.fill(execution_price, amount, commission)
            
            # 记录到已成交订单
            self.filled_orders.append(order)
            
            return order
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"模拟市价单执行失败: {e}")
            return None
    
    def simulate_limit_order(self, symbol: str, side: str, amount: float, 
                           limit_price: float, market_data: pd.DataFrame) -> Optional[Order]:
        """
        模拟限价单执行（用于回测）
        
        Args:
            symbol: 交易对
            side: 买卖方向
            amount: 数量
            limit_price: 限价
            market_data: 市场数据
            
        Returns:
            执行后的订单（如果触发）
        """
        try:
            if market_data.empty:
                return None
            
            current_bar = market_data.iloc[-1]
            
            # 检查是否触发限价单
            triggered = False
            execution_price = limit_price
            
            if side == OrderType.BUY:
                # 买单：当前价格低于或等于限价时触发
                if current_bar['low'] <= limit_price:
                    triggered = True
                    execution_price = min(limit_price, current_bar['open'])
            else:
                # 卖单：当前价格高于或等于限价时触发
                if current_bar['high'] >= limit_price:
                    triggered = True
                    execution_price = max(limit_price, current_bar['open'])
            
            if not triggered:
                return None
            
            # 创建并执行订单
            order = Order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=execution_price,
                order_type="limit"
            )
            
            # 计算手续费
            commission = amount * execution_price * self.commission_rate
            
            # 填充订单
            order.fill(execution_price, amount, commission)
            
            # 记录到已成交订单
            self.filled_orders.append(order)
            
            return order
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"模拟限价单执行失败: {e}")
            return None
    
    def _get_current_price(self, symbol: str) -> Optional[Dict]:
        """获取当前价格"""
        try:
            if self.data_module:
                return self.data_module.get_ticker(symbol)
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取{symbol}价格失败: {e}")
            return None
    
    def _apply_slippage(self, price: float, side: str) -> float:
        """应用滑点"""
        if side == OrderType.BUY:
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)
    
    def get_order_status(self, order_id: str) -> Optional[str]:
        """获取订单状态"""
        # 检查待处理订单
        if order_id in self.pending_orders:
            return self.pending_orders[order_id].status
        
        # 检查已成交订单
        for order in self.filled_orders:
            if order.order_id == order_id:
                return order.status
        
        # 检查已取消订单
        for order in self.cancelled_orders:
            if order.order_id == order_id:
                return order.status
        
        return None
    
    def get_filled_orders(self, symbol: str = None) -> List[Order]:
        """获取已成交订单"""
        if symbol:
            return [order for order in self.filled_orders if order.symbol == symbol]
        return self.filled_orders.copy()
    
    def get_pending_orders(self, symbol: str = None) -> List[Order]:
        """获取待处理订单"""
        orders = list(self.pending_orders.values())
        if symbol:
            return [order for order in orders if order.symbol == symbol]
        return orders
    
    def get_execution_statistics(self) -> Dict:
        """获取执行统计信息"""
        try:
            total_orders = len(self.filled_orders) + len(self.cancelled_orders)
            filled_count = len(self.filled_orders)
            cancelled_count = len(self.cancelled_orders)
            
            if filled_count > 0:
                total_commission = sum(order.commission for order in self.filled_orders)
                avg_commission = total_commission / filled_count
                
                # 按交易对统计
                symbol_stats = {}
                for order in self.filled_orders:
                    if order.symbol not in symbol_stats:
                        symbol_stats[order.symbol] = {'count': 0, 'volume': 0, 'commission': 0}
                    
                    symbol_stats[order.symbol]['count'] += 1
                    symbol_stats[order.symbol]['volume'] += order.filled_amount * order.filled_price
                    symbol_stats[order.symbol]['commission'] += order.commission
            else:
                total_commission = 0
                avg_commission = 0
                symbol_stats = {}
            
            return {
                'total_orders': total_orders,
                'filled_orders': filled_count,
                'cancelled_orders': cancelled_count,
                'fill_rate': filled_count / total_orders if total_orders > 0 else 0,
                'total_commission': total_commission,
                'avg_commission': avg_commission,
                'symbol_statistics': symbol_stats
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取执行统计失败: {e}")
            return {}
    
    def reset(self):
        """重置执行模块状态（用于回测）"""
        self.pending_orders = {}
        self.filled_orders = []
        self.cancelled_orders = []
    
    def process_pending_orders(self, current_prices: Dict[str, float]):
        """处理待处理订单"""
        orders_to_remove = []
        
        for order_id, order in self.pending_orders.items():
            try:
                if order.symbol in current_prices:
                    current_price = current_prices[order.symbol]
                    
                    # 市价单立即执行
                    if order.order_type == "market":
                        if self.execute_order(order, current_price):
                            orders_to_remove.append(order_id)
                    
                    # 限价单检查触发条件
                    elif order.order_type == "limit":
                        triggered = False
                        
                        if order.side == OrderType.BUY and current_price <= order.price:
                            triggered = True
                        elif order.side == OrderType.SELL and current_price >= order.price:
                            triggered = True
                        
                        if triggered:
                            if self.execute_order(order, order.price):
                                orders_to_remove.append(order_id)
                                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"处理订单{order_id}失败: {e}")
        
        # 移除已处理的订单
        for order_id in orders_to_remove:
            if order_id in self.pending_orders:
                del self.pending_orders[order_id]
