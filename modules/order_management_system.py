"""
TradeFan 专业订单管理系统 (OMS)
支持智能执行算法、实时风控和订单生命周期管理

架构设计:
交易信号 → 风险检查 → 订单生成 → 执行路由 → 状态追踪
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"           # 待处理
    SUBMITTED = "submitted"       # 已提交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    FILLED = "filled"            # 完全成交
    CANCELLED = "cancelled"      # 已取消
    REJECTED = "rejected"        # 被拒绝
    EXPIRED = "expired"          # 已过期
    FAILED = "failed"            # 执行失败


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"            # 市价单
    LIMIT = "limit"              # 限价单
    STOP = "stop"                # 止损单
    STOP_LIMIT = "stop_limit"    # 止损限价单
    ICEBERG = "iceberg"          # 冰山单
    TWAP = "twap"               # 时间加权平均价格
    VWAP = "vwap"               # 成交量加权平均价格


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderRequest:
    """订单请求"""
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    client_order_id: Optional[str] = None
    strategy_id: Optional[str] = None
    
    # 高级执行参数
    iceberg_qty: Optional[float] = None  # 冰山单显示数量
    twap_duration: Optional[int] = None  # TWAP执行时长(秒)
    max_participation_rate: Optional[float] = None  # 最大参与率
    
    def __post_init__(self):
        if not self.client_order_id:
            self.client_order_id = str(uuid.uuid4())


@dataclass
class Order:
    """订单对象"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    created_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    strategy_id: Optional[str] = None
    
    # 执行统计
    fills: List[Dict[str, Any]] = field(default_factory=list)
    execution_report: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def remaining_quantity(self) -> float:
        """剩余数量"""
        return self.quantity - self.filled_quantity
    
    @property
    def fill_percentage(self) -> float:
        """成交百分比"""
        return (self.filled_quantity / self.quantity) * 100 if self.quantity > 0 else 0
    
    def add_fill(self, fill_quantity: float, fill_price: float, commission: float = 0.0):
        """添加成交记录"""
        self.fills.append({
            "quantity": fill_quantity,
            "price": fill_price,
            "commission": commission,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # 更新订单状态
        self.filled_quantity += fill_quantity
        self.commission += commission
        
        # 计算平均成交价
        total_value = sum(fill["quantity"] * fill["price"] for fill in self.fills)
        self.avg_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else 0
        
        # 更新订单状态
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_time = datetime.now(timezone.utc)


class RiskCheckResult:
    """风控检查结果"""
    
    def __init__(self, passed: bool, reason: str = "", risk_score: float = 0.0):
        self.passed = passed
        self.reason = reason
        self.risk_score = risk_score
        self.timestamp = datetime.now(timezone.utc)


class RealTimeRiskEngine:
    """实时风控引擎"""
    
    def __init__(self):
        self.position_limits = {}  # 仓位限制
        self.daily_loss_limits = {}  # 日损失限制
        self.concentration_limits = {}  # 集中度限制
        self.velocity_limits = {}  # 交易频率限制
        self.logger = logging.getLogger(__name__)
        
        # 风控统计
        self.daily_pnl = {}
        self.position_sizes = {}
        self.order_count_today = {}
        
    def set_position_limit(self, symbol: str, max_position: float):
        """设置仓位限制"""
        self.position_limits[symbol] = max_position
    
    def set_daily_loss_limit(self, strategy_id: str, max_loss: float):
        """设置日损失限制"""
        self.daily_loss_limits[strategy_id] = max_loss
    
    async def pre_trade_check(self, order_request: OrderRequest) -> RiskCheckResult:
        """交易前风控检查"""
        try:
            # 1. 仓位限制检查
            position_check = await self._check_position_limits(order_request)
            if not position_check.passed:
                return position_check
            
            # 2. 日损失限制检查
            loss_check = await self._check_daily_loss_limits(order_request)
            if not loss_check.passed:
                return loss_check
            
            # 3. 集中度检查
            concentration_check = await self._check_concentration_limits(order_request)
            if not concentration_check.passed:
                return concentration_check
            
            # 4. 交易频率检查
            velocity_check = await self._check_velocity_limits(order_request)
            if not velocity_check.passed:
                return velocity_check
            
            # 5. 市场风险检查
            market_check = await self._check_market_conditions(order_request)
            if not market_check.passed:
                return market_check
            
            return RiskCheckResult(True, "All risk checks passed")
            
        except Exception as e:
            self.logger.error(f"Risk check error: {e}")
            return RiskCheckResult(False, f"Risk check failed: {e}")
    
    async def _check_position_limits(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查仓位限制"""
        symbol = order_request.symbol
        if symbol not in self.position_limits:
            return RiskCheckResult(True)
        
        current_position = self.position_sizes.get(symbol, 0.0)
        new_position = current_position
        
        if order_request.side == OrderSide.BUY:
            new_position += order_request.quantity
        else:
            new_position -= order_request.quantity
        
        max_position = self.position_limits[symbol]
        if abs(new_position) > max_position:
            return RiskCheckResult(
                False, 
                f"Position limit exceeded: {abs(new_position)} > {max_position}"
            )
        
        return RiskCheckResult(True)
    
    async def _check_daily_loss_limits(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查日损失限制"""
        if not order_request.strategy_id:
            return RiskCheckResult(True)
        
        strategy_id = order_request.strategy_id
        if strategy_id not in self.daily_loss_limits:
            return RiskCheckResult(True)
        
        current_pnl = self.daily_pnl.get(strategy_id, 0.0)
        max_loss = self.daily_loss_limits[strategy_id]
        
        if current_pnl < -max_loss:
            return RiskCheckResult(
                False,
                f"Daily loss limit exceeded: {current_pnl} < -{max_loss}"
            )
        
        return RiskCheckResult(True)
    
    async def _check_concentration_limits(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查集中度限制"""
        # 简化实现：检查单一品种占比
        symbol = order_request.symbol
        total_exposure = sum(abs(pos) for pos in self.position_sizes.values())
        
        if total_exposure == 0:
            return RiskCheckResult(True)
        
        current_exposure = abs(self.position_sizes.get(symbol, 0.0))
        concentration = current_exposure / total_exposure
        
        # 单一品种不超过50%
        if concentration > 0.5:
            return RiskCheckResult(
                False,
                f"Concentration limit exceeded: {concentration:.2%} > 50%"
            )
        
        return RiskCheckResult(True)
    
    async def _check_velocity_limits(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查交易频率限制"""
        today = datetime.now().date()
        key = f"{order_request.symbol}_{today}"
        
        current_count = self.order_count_today.get(key, 0)
        max_orders_per_day = 100  # 每日最大订单数
        
        if current_count >= max_orders_per_day:
            return RiskCheckResult(
                False,
                f"Daily order limit exceeded: {current_count} >= {max_orders_per_day}"
            )
        
        return RiskCheckResult(True)
    
    async def _check_market_conditions(self, order_request: OrderRequest) -> RiskCheckResult:
        """检查市场条件"""
        # 简化实现：检查市场开放时间等
        # 实际应用中可以检查波动率、流动性等
        return RiskCheckResult(True)
    
    def update_position(self, symbol: str, quantity_change: float):
        """更新仓位"""
        if symbol not in self.position_sizes:
            self.position_sizes[symbol] = 0.0
        self.position_sizes[symbol] += quantity_change
    
    def update_pnl(self, strategy_id: str, pnl_change: float):
        """更新损益"""
        if strategy_id not in self.daily_pnl:
            self.daily_pnl[strategy_id] = 0.0
        self.daily_pnl[strategy_id] += pnl_change


class ExecutionAlgorithms:
    """智能执行算法"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def twap(self, order: Order, duration_seconds: int, 
                   market_data_callback: Callable) -> List[OrderRequest]:
        """时间加权平均价格算法"""
        try:
            # 计算子订单参数
            num_slices = max(1, duration_seconds // 60)  # 每分钟一个子订单
            slice_quantity = order.quantity / num_slices
            slice_interval = duration_seconds / num_slices
            
            child_orders = []
            
            for i in range(num_slices):
                child_order = OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=OrderType.MARKET,  # TWAP通常使用市价单
                    quantity=slice_quantity,
                    strategy_id=order.strategy_id,
                    client_order_id=f"{order.client_order_id}_twap_{i}"
                )
                child_orders.append(child_order)
            
            return child_orders
            
        except Exception as e:
            self.logger.error(f"TWAP algorithm error: {e}")
            return []
    
    async def vwap(self, order: Order, historical_volume: pd.Series) -> List[OrderRequest]:
        """成交量加权平均价格算法"""
        try:
            if historical_volume.empty:
                # 如果没有历史数据，回退到等量拆分
                return await self._equal_split(order, 10)
            
            # 根据历史成交量分布拆分订单
            total_volume = historical_volume.sum()
            volume_weights = historical_volume / total_volume
            
            child_orders = []
            remaining_quantity = order.quantity
            
            for i, weight in enumerate(volume_weights):
                if remaining_quantity <= 0:
                    break
                
                slice_quantity = min(order.quantity * weight, remaining_quantity)
                if slice_quantity < 0.001:  # 最小订单量
                    continue
                
                child_order = OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=OrderType.MARKET,
                    quantity=slice_quantity,
                    strategy_id=order.strategy_id,
                    client_order_id=f"{order.client_order_id}_vwap_{i}"
                )
                child_orders.append(child_order)
                remaining_quantity -= slice_quantity
            
            return child_orders
            
        except Exception as e:
            self.logger.error(f"VWAP algorithm error: {e}")
            return await self._equal_split(order, 10)
    
    async def iceberg(self, order: Order, visible_quantity: float) -> List[OrderRequest]:
        """冰山算法"""
        try:
            child_orders = []
            remaining_quantity = order.quantity
            slice_count = 0
            
            while remaining_quantity > 0:
                slice_quantity = min(visible_quantity, remaining_quantity)
                
                child_order = OrderRequest(
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=slice_quantity,
                    price=order.price,
                    strategy_id=order.strategy_id,
                    client_order_id=f"{order.client_order_id}_iceberg_{slice_count}"
                )
                child_orders.append(child_order)
                
                remaining_quantity -= slice_quantity
                slice_count += 1
            
            return child_orders
            
        except Exception as e:
            self.logger.error(f"Iceberg algorithm error: {e}")
            return []
    
    async def _equal_split(self, order: Order, num_slices: int) -> List[OrderRequest]:
        """等量拆分"""
        slice_quantity = order.quantity / num_slices
        child_orders = []
        
        for i in range(num_slices):
            child_order = OrderRequest(
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=slice_quantity,
                price=order.price,
                strategy_id=order.strategy_id,
                client_order_id=f"{order.client_order_id}_split_{i}"
            )
            child_orders.append(child_order)
        
        return child_orders


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.active_orders: Dict[str, Order] = {}
        self.order_history: Dict[str, Order] = {}
        self.risk_engine = RealTimeRiskEngine()
        self.execution_algos = ExecutionAlgorithms()
        self.logger = logging.getLogger(__name__)
        
        # 回调函数
        self.order_update_callbacks: List[Callable] = []
        self.fill_callbacks: List[Callable] = []
    
    def add_order_update_callback(self, callback: Callable):
        """添加订单更新回调"""
        self.order_update_callbacks.append(callback)
    
    def add_fill_callback(self, callback: Callable):
        """添加成交回调"""
        self.fill_callbacks.append(callback)
    
    async def submit_order(self, order_request: OrderRequest) -> Optional[Order]:
        """提交订单"""
        try:
            # 1. 预风控检查
            risk_check = await self.risk_engine.pre_trade_check(order_request)
            if not risk_check.passed:
                self.logger.warning(f"Order rejected by risk check: {risk_check.reason}")
                return None
            
            # 2. 创建订单对象
            order = Order(
                order_id=str(uuid.uuid4()),
                client_order_id=order_request.client_order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_request.price,
                stop_price=order_request.stop_price,
                status=OrderStatus.PENDING,
                strategy_id=order_request.strategy_id
            )
            
            # 3. 选择执行算法
            if order_request.order_type == OrderType.TWAP:
                child_orders = await self.execution_algos.twap(
                    order, order_request.twap_duration or 300, None
                )
                # 执行子订单
                for child_order_request in child_orders:
                    await self._execute_child_order(child_order_request, order)
            
            elif order_request.order_type == OrderType.ICEBERG:
                child_orders = await self.execution_algos.iceberg(
                    order, order_request.iceberg_qty or (order_request.quantity * 0.1)
                )
                # 执行第一个子订单
                if child_orders:
                    await self._execute_child_order(child_orders[0], order)
            
            else:
                # 直接执行普通订单
                await self._execute_order(order)
            
            # 4. 添加到活跃订单
            self.active_orders[order.order_id] = order
            
            # 5. 通知回调
            await self._notify_order_update(order)
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error submitting order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        try:
            if order_id not in self.active_orders:
                self.logger.warning(f"Order {order_id} not found")
                return False
            
            order = self.active_orders[order_id]
            
            # 模拟取消订单
            order.status = OrderStatus.CANCELLED
            order.updated_time = datetime.now(timezone.utc)
            
            # 移动到历史订单
            self.order_history[order_id] = order
            del self.active_orders[order_id]
            
            await self._notify_order_update(order)
            
            self.logger.info(f"Order {order_id} cancelled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False
    
    async def modify_order(self, order_id: str, new_quantity: Optional[float] = None,
                          new_price: Optional[float] = None) -> bool:
        """修改订单"""
        try:
            if order_id not in self.active_orders:
                return False
            
            order = self.active_orders[order_id]
            
            if new_quantity is not None:
                order.quantity = new_quantity
            if new_price is not None:
                order.price = new_price
            
            order.updated_time = datetime.now(timezone.utc)
            await self._notify_order_update(order)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error modifying order: {e}")
            return False
    
    async def _execute_order(self, order: Order):
        """执行订单（模拟）"""
        # 模拟订单执行
        order.status = OrderStatus.SUBMITTED
        
        # 模拟部分成交
        await asyncio.sleep(0.1)  # 模拟网络延迟
        
        # 模拟成交
        fill_quantity = order.quantity
        fill_price = order.price or 45000.0  # 模拟价格
        
        order.add_fill(fill_quantity, fill_price, fill_quantity * fill_price * 0.001)
        
        # 更新风控统计
        quantity_change = fill_quantity if order.side == OrderSide.BUY else -fill_quantity
        self.risk_engine.update_position(order.symbol, quantity_change)
        
        await self._notify_fill(order, fill_quantity, fill_price)
    
    async def _execute_child_order(self, child_order_request: OrderRequest, parent_order: Order):
        """执行子订单"""
        # 简化实现：直接模拟成交
        fill_quantity = child_order_request.quantity
        fill_price = child_order_request.price or 45000.0
        
        parent_order.add_fill(fill_quantity, fill_price, fill_quantity * fill_price * 0.001)
        
        await self._notify_fill(parent_order, fill_quantity, fill_price)
    
    async def _notify_order_update(self, order: Order):
        """通知订单更新"""
        for callback in self.order_update_callbacks:
            try:
                await callback(order)
            except Exception as e:
                self.logger.error(f"Error in order update callback: {e}")
    
    async def _notify_fill(self, order: Order, fill_quantity: float, fill_price: float):
        """通知成交"""
        for callback in self.fill_callbacks:
            try:
                await callback(order, fill_quantity, fill_price)
            except Exception as e:
                self.logger.error(f"Error in fill callback: {e}")
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """获取订单状态"""
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        elif order_id in self.order_history:
            return self.order_history[order_id]
        return None
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """获取活跃订单"""
        orders = list(self.active_orders.values())
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        return orders
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """获取订单统计"""
        all_orders = list(self.active_orders.values()) + list(self.order_history.values())
        
        if not all_orders:
            return {}
        
        total_orders = len(all_orders)
        filled_orders = len([o for o in all_orders if o.status == OrderStatus.FILLED])
        cancelled_orders = len([o for o in all_orders if o.status == OrderStatus.CANCELLED])
        
        total_volume = sum(o.filled_quantity for o in all_orders)
        total_commission = sum(o.commission for o in all_orders)
        
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "cancelled_orders": cancelled_orders,
            "fill_rate": filled_orders / total_orders if total_orders > 0 else 0,
            "total_volume": total_volume,
            "total_commission": total_commission,
            "avg_fill_price": sum(o.avg_fill_price for o in all_orders if o.filled_quantity > 0) / max(1, filled_orders)
        }


# 全局订单管理器实例
order_manager = None

def get_order_manager() -> OrderManager:
    """获取订单管理器实例"""
    global order_manager
    if order_manager is None:
        order_manager = OrderManager()
    return order_manager


# 使用示例
async def example_usage():
    """使用示例"""
    om = get_order_manager()
    
    # 添加回调函数
    async def on_order_update(order: Order):
        print(f"Order update: {order.order_id} - {order.status}")
    
    async def on_fill(order: Order, quantity: float, price: float):
        print(f"Fill: {order.order_id} - {quantity}@{price}")
    
    om.add_order_update_callback(on_order_update)
    om.add_fill_callback(on_fill)
    
    # 设置风控参数
    om.risk_engine.set_position_limit("BTC/USDT", 10.0)
    om.risk_engine.set_daily_loss_limit("strategy_1", 1000.0)
    
    # 提交市价单
    market_order = OrderRequest(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        strategy_id="strategy_1"
    )
    
    order = await om.submit_order(market_order)
    if order:
        print(f"Market order submitted: {order.order_id}")
    
    # 提交TWAP订单
    twap_order = OrderRequest(
        symbol="BTC/USDT",
        side=OrderSide.SELL,
        order_type=OrderType.TWAP,
        quantity=5.0,
        twap_duration=300,  # 5分钟
        strategy_id="strategy_1"
    )
    
    order = await om.submit_order(twap_order)
    if order:
        print(f"TWAP order submitted: {order.order_id}")
    
    # 提交冰山订单
    iceberg_order = OrderRequest(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.ICEBERG,
        quantity=10.0,
        price=44000.0,
        iceberg_qty=2.0,  # 每次显示2个单位
        strategy_id="strategy_1"
    )
    
    order = await om.submit_order(iceberg_order)
    if order:
        print(f"Iceberg order submitted: {order.order_id}")
    
    # 等待执行
    await asyncio.sleep(2)
    
    # 查看统计
    stats = om.get_order_statistics()
    print(f"Order statistics: {stats}")
    
    # 查看活跃订单
    active_orders = om.get_active_orders()
    print(f"Active orders: {len(active_orders)}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
