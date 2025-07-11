"""
实盘模拟交易执行模块
支持Binance Testnet API真实下单
"""

import ccxt
import asyncio
import websockets
import json
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
from .log_module import LogModule
from .utils import Order, OrderStatus, OrderType

class LiveExecutionModule:
    """实盘模拟交易执行模块"""
    
    def __init__(self, config: Dict, logger: LogModule = None):
        self.config = config
        self.logger = logger or LogModule()
        
        # 初始化交易所连接
        self.exchange = self._init_exchange()
        
        # 交易状态
        self.positions = {}  # 持仓信息
        self.orders = {}     # 订单记录
        self.balance = {}    # 账户余额
        
        # WebSocket连接
        self.ws_connections = {}
        self.price_callbacks = []  # 价格更新回调函数
        
        # 交易统计
        self.trade_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': 0,
            'total_commission': 0
        }
        
        self.logger.info("实盘模拟执行模块初始化完成")
    
    def _init_exchange(self) -> ccxt.Exchange:
        """初始化交易所连接"""
        try:
            exchange = ccxt.binance({
                'apiKey': self.config.get('api_key', ''),
                'secret': self.config.get('secret', ''),
                'sandbox': self.config.get('sandbox', True),  # 使用测试网
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # 现货交易
                }
            })
            
            # 测试连接
            exchange.load_markets()
            self.logger.info(f"交易所连接成功: {exchange.id} (测试网: {exchange.sandbox})")
            
            return exchange
            
        except Exception as e:
            self.logger.error(f"交易所连接失败: {e}")
            raise
    
    async def start_price_stream(self, symbols: List[str]):
        """启动实时价格流"""
        self.logger.info(f"启动价格流: {symbols}")
        
        # Binance WebSocket URL
        base_url = "wss://testnet.binance.vision/ws/"
        
        # 构建订阅消息
        streams = []
        for symbol in symbols:
            # 转换符号格式 BTC/USDT -> btcusdt
            stream_symbol = symbol.replace('/', '').lower()
            streams.append(f"{stream_symbol}@ticker")
        
        stream_url = base_url + "/".join(streams)
        
        try:
            async with websockets.connect(stream_url) as websocket:
                self.logger.info("WebSocket连接已建立")
                
                async for message in websocket:
                    data = json.loads(message)
                    await self._handle_price_update(data)
                    
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
            # 重连逻辑
            await asyncio.sleep(5)
            await self.start_price_stream(symbols)
    
    async def _handle_price_update(self, data: Dict):
        """处理价格更新"""
        try:
            if 'c' in data:  # 最新价格
                symbol = data['s']  # BTCUSDT
                price = float(data['c'])
                
                # 转换符号格式
                formatted_symbol = f"{symbol[:-4]}/{symbol[-4:]}"  # BTCUSDT -> BTC/USDT
                
                # 调用价格回调函数
                for callback in self.price_callbacks:
                    await callback(formatted_symbol, price, data)
                    
        except Exception as e:
            self.logger.error(f"价格更新处理错误: {e}")
    
    def add_price_callback(self, callback: Callable):
        """添加价格更新回调函数"""
        self.price_callbacks.append(callback)
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         order_type: str = 'market', price: float = None) -> Optional[Order]:
        """下单"""
        try:
            self.logger.info(f"准备下单: {symbol} {side} {amount} @ {price or 'market'}")
            
            # 风险检查
            if not self._pre_order_check(symbol, side, amount, price):
                return None
            
            # 构建订单参数
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount
            }
            
            if order_type == 'limit' and price:
                order_params['price'] = price
            
            # 发送订单到交易所
            if self.config.get('paper_trading', True):
                # 模拟交易模式
                result = await self._simulate_order(order_params)
            else:
                # 真实交易模式
                result = self.exchange.create_order(**order_params)
            
            # 创建订单对象
            order = Order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price or result.get('price', 0),
                order_type=order_type,
                order_id=result.get('id', '')
            )
            
            # 填充订单
            order.fill(
                price=result.get('price', price or 0),
                amount=result.get('filled', amount),
                commission=result.get('fee', {}).get('cost', 0)
            )
            
            # 记录订单
            self.orders[order.order_id] = order
            
            # 更新统计
            self.trade_stats['total_trades'] += 1
            self.trade_stats['successful_trades'] += 1
            self.trade_stats['total_volume'] += amount * order.filled_price
            self.trade_stats['total_commission'] += order.commission
            
            # 更新持仓
            await self._update_position(symbol, side, order.filled_amount, order.filled_price)
            
            self.logger.info(f"订单执行成功: {order.order_id}")
            return order
            
        except Exception as e:
            self.logger.error(f"下单失败: {e}")
            self.trade_stats['failed_trades'] += 1
            return None
    
    def _pre_order_check(self, symbol: str, side: str, amount: float, price: float) -> bool:
        """订单前置检查"""
        try:
            # 检查余额
            if not self._check_balance(symbol, side, amount, price):
                self.logger.warning(f"余额不足: {symbol} {side} {amount}")
                return False
            
            # 检查最小交易量
            market = self.exchange.market(symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            if amount < min_amount:
                self.logger.warning(f"交易量低于最小限制: {amount} < {min_amount}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"订单检查失败: {e}")
            return False
    
    def _check_balance(self, symbol: str, side: str, amount: float, price: float) -> bool:
        """检查账户余额"""
        try:
            balance = self.get_balance()
            
            if side == 'buy':
                # 买入需要检查报价货币余额
                quote_currency = symbol.split('/')[1]  # USDT
                required = amount * (price or self.get_current_price(symbol))
                available = balance.get(quote_currency, {}).get('free', 0)
                return available >= required
            else:
                # 卖出需要检查基础货币余额
                base_currency = symbol.split('/')[0]  # BTC
                available = balance.get(base_currency, {}).get('free', 0)
                return available >= amount
                
        except Exception as e:
            self.logger.error(f"余额检查失败: {e}")
            return False
    
    async def _simulate_order(self, params: Dict) -> Dict:
        """模拟订单执行"""
        # 获取当前价格
        current_price = self.get_current_price(params['symbol'])
        
        # 模拟订单结果
        result = {
            'id': f"sim_{int(time.time() * 1000)}",
            'symbol': params['symbol'],
            'type': params['type'],
            'side': params['side'],
            'amount': params['amount'],
            'price': current_price,
            'filled': params['amount'],
            'status': 'closed',
            'fee': {
                'cost': params['amount'] * current_price * 0.001,  # 0.1% 手续费
                'currency': params['symbol'].split('/')[1]
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    async def _update_position(self, symbol: str, side: str, amount: float, price: float):
        """更新持仓信息"""
        if symbol not in self.positions:
            self.positions[symbol] = {
                'size': 0,
                'entry_price': 0,
                'unrealized_pnl': 0,
                'realized_pnl': 0
            }
        
        position = self.positions[symbol]
        
        if side == 'buy':
            # 买入增加持仓
            total_cost = position['size'] * position['entry_price'] + amount * price
            position['size'] += amount
            position['entry_price'] = total_cost / position['size'] if position['size'] > 0 else 0
        else:
            # 卖出减少持仓
            if position['size'] >= amount:
                # 计算已实现盈亏
                realized_pnl = (price - position['entry_price']) * amount
                position['realized_pnl'] += realized_pnl
                position['size'] -= amount
                
                if position['size'] == 0:
                    position['entry_price'] = 0
            else:
                self.logger.warning(f"卖出数量超过持仓: {amount} > {position['size']}")
    
    def get_balance(self) -> Dict:
        """获取账户余额"""
        try:
            if self.config.get('paper_trading', True):
                # 模拟余额
                return {
                    'USDT': {'free': 10000, 'used': 0, 'total': 10000},
                    'BTC': {'free': 0, 'used': 0, 'total': 0},
                    'ETH': {'free': 0, 'used': 0, 'total': 0}
                }
            else:
                return self.exchange.fetch_balance()
                
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            return {}
    
    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"获取价格失败: {e}")
            return 0
    
    def get_positions(self) -> Dict:
        """获取持仓信息"""
        return self.positions.copy()
    
    def get_orders(self, symbol: str = None) -> List[Order]:
        """获取订单记录"""
        if symbol:
            return [order for order in self.orders.values() if order.symbol == symbol]
        return list(self.orders.values())
    
    def get_trade_stats(self) -> Dict:
        """获取交易统计"""
        return self.trade_stats.copy()
    
    async def close_all_positions(self):
        """平仓所有持仓"""
        self.logger.info("开始平仓所有持仓")
        
        for symbol, position in self.positions.items():
            if position['size'] > 0:
                await self.place_order(symbol, 'sell', position['size'])
        
        self.logger.info("所有持仓已平仓")
    
    def stop(self):
        """停止执行模块"""
        self.logger.info("停止实盘模拟执行模块")
        # 关闭WebSocket连接等清理工作
