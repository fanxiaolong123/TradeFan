"""
TradeFan Binance API 连接器
安全的Binance API集成，支持现货和期货交易
"""

import asyncio
import hmac
import hashlib
import time
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import pandas as pd
from urllib.parse import urlencode


class BinanceConnector:
    """Binance API连接器"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)
        
        # API端点
        if testnet:
            self.base_url = "https://testnet.binance.vision"
            self.futures_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://api.binance.com"
            self.futures_url = "https://fapi.binance.com"
        
        # 会话管理
        self.session = None
        self.rate_limit_info = {}
        
        # 交易对信息缓存
        self.exchange_info = {}
        self.symbol_info = {}
        
        self.logger.info(f"BinanceConnector initialized (testnet: {testnet})")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def initialize(self):
        """初始化连接"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'X-MBX-APIKEY': self.api_key}
            )
            
            # 获取交易所信息
            await self._load_exchange_info()
            
            # 测试连接
            await self.test_connectivity()
            
            self.logger.info("Binance connector initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Binance connector: {e}")
            raise
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.logger.info("Binance connector closed")
    
    def _generate_signature(self, params: Dict) -> str:
        """生成API签名"""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None,
                           signed: bool = False, futures: bool = False) -> Dict:
        """发送API请求"""
        if not self.session:
            raise RuntimeError("Connector not initialized")
        
        params = params or {}
        base_url = self.futures_url if futures else self.base_url
        url = f"{base_url}{endpoint}"
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        try:
            if method.upper() == 'GET':
                async with self.session.get(url, params=params) as response:
                    return await self._handle_response(response)
            elif method.upper() == 'POST':
                async with self.session.post(url, data=params) as response:
                    return await self._handle_response(response)
            elif method.upper() == 'DELETE':
                async with self.session.delete(url, params=params) as response:
                    return await self._handle_response(response)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            raise
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict:
        """处理API响应"""
        # 更新速率限制信息
        self.rate_limit_info.update({
            'used_weight': response.headers.get('X-MBX-USED-WEIGHT-1M'),
            'order_count': response.headers.get('X-MBX-ORDER-COUNT-1M'),
        })
        
        if response.status == 200:
            return await response.json()
        else:
            error_text = await response.text()
            self.logger.error(f"API error {response.status}: {error_text}")
            raise Exception(f"Binance API error {response.status}: {error_text}")
    
    async def test_connectivity(self) -> bool:
        """测试连接"""
        try:
            result = await self._make_request('GET', '/api/v3/ping')
            self.logger.info("Connectivity test passed")
            return True
        except Exception as e:
            self.logger.error(f"Connectivity test failed: {e}")
            return False
    
    async def get_server_time(self) -> int:
        """获取服务器时间"""
        result = await self._make_request('GET', '/api/v3/time')
        return result['serverTime']
    
    async def _load_exchange_info(self):
        """加载交易所信息"""
        try:
            # 现货交易所信息
            spot_info = await self._make_request('GET', '/api/v3/exchangeInfo')
            self.exchange_info['spot'] = spot_info
            
            # 期货交易所信息
            try:
                futures_info = await self._make_request('GET', '/fapi/v1/exchangeInfo', futures=True)
                self.exchange_info['futures'] = futures_info
            except:
                self.logger.warning("Failed to load futures exchange info")
            
            # 构建交易对信息映射
            for symbol_info in spot_info['symbols']:
                symbol = symbol_info['symbol']
                self.symbol_info[symbol] = {
                    'baseAsset': symbol_info['baseAsset'],
                    'quoteAsset': symbol_info['quoteAsset'],
                    'status': symbol_info['status'],
                    'filters': {f['filterType']: f for f in symbol_info['filters']},
                    'type': 'spot'
                }
            
            self.logger.info(f"Loaded info for {len(self.symbol_info)} symbols")
            
        except Exception as e:
            self.logger.error(f"Failed to load exchange info: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """获取账户信息"""
        return await self._make_request('GET', '/api/v3/account', signed=True)
    
    async def get_balance(self, asset: str = None) -> Dict:
        """获取余额"""
        account_info = await self.get_account_info()
        balances = {b['asset']: {
            'free': float(b['free']),
            'locked': float(b['locked']),
            'total': float(b['free']) + float(b['locked'])
        } for b in account_info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
        
        if asset:
            return balances.get(asset, {'free': 0, 'locked': 0, 'total': 0})
        return balances
    
    async def get_symbol_price(self, symbol: str) -> float:
        """获取交易对价格"""
        result = await self._make_request('GET', '/api/v3/ticker/price', {'symbol': symbol})
        return float(result['price'])
    
    async def get_all_prices(self) -> Dict[str, float]:
        """获取所有交易对价格"""
        result = await self._make_request('GET', '/api/v3/ticker/price')
        return {item['symbol']: float(item['price']) for item in result}
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 500,
                        start_time: int = None, end_time: int = None) -> pd.DataFrame:
        """获取K线数据"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1000)  # Binance限制
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        result = await self._make_request('GET', '/api/v3/klines', params)
        
        # 转换为DataFrame
        df = pd.DataFrame(result, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades_count',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        
        # 数据类型转换
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        return df
    
    async def place_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, price: float = None,
                         time_in_force: str = 'GTC',
                         test: bool = True) -> Dict:
        """下单"""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': self._format_quantity(symbol, quantity),
            'timeInForce': time_in_force
        }
        
        if price and order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
            params['price'] = self._format_price(symbol, price)
        
        endpoint = '/api/v3/order/test' if test else '/api/v3/order'
        
        try:
            result = await self._make_request('POST', endpoint, params, signed=True)
            self.logger.info(f"Order placed: {symbol} {side} {quantity} @ {price}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: int = None,
                          client_order_id: str = None) -> Dict:
        """取消订单"""
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            raise ValueError("Must provide either order_id or client_order_id")
        
        return await self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """获取未成交订单"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    async def get_order_history(self, symbol: str, limit: int = 500) -> List[Dict]:
        """获取历史订单"""
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        
        return await self._make_request('GET', '/api/v3/allOrders', params, signed=True)
    
    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """格式化数量"""
        if symbol in self.symbol_info:
            lot_size_filter = self.symbol_info[symbol]['filters'].get('LOT_SIZE')
            if lot_size_filter:
                step_size = float(lot_size_filter['stepSize'])
                precision = len(str(step_size).split('.')[-1].rstrip('0'))
                return f"{quantity:.{precision}f}"
        
        return f"{quantity:.8f}".rstrip('0').rstrip('.')
    
    def _format_price(self, symbol: str, price: float) -> str:
        """格式化价格"""
        if symbol in self.symbol_info:
            price_filter = self.symbol_info[symbol]['filters'].get('PRICE_FILTER')
            if price_filter:
                tick_size = float(price_filter['tickSize'])
                precision = len(str(tick_size).split('.')[-1].rstrip('0'))
                return f"{price:.{precision}f}"
        
        return f"{price:.8f}".rstrip('0').rstrip('.')
    
    def get_trading_fees(self, symbol: str) -> Dict:
        """获取交易手续费信息"""
        # 默认费率，实际应该从API获取
        return {
            'maker': 0.001,  # 0.1%
            'taker': 0.001   # 0.1%
        }
    
    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """获取24小时价格变动统计"""
        params = {'symbol': symbol}
        return await self._make_request('GET', '/api/v3/ticker/24hr', params)
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """获取订单簿"""
        params = {
            'symbol': symbol,
            'limit': min(limit, 5000)
        }
        return await self._make_request('GET', '/api/v3/depth', params)
    
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict]:
        """获取最近成交"""
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }
        return await self._make_request('GET', '/api/v3/trades', params)


class BinanceTradingBot:
    """Binance交易机器人"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.connector = BinanceConnector(api_key, api_secret, testnet)
        self.logger = logging.getLogger(__name__)
        
        # 交易状态
        self.is_running = False
        self.positions = {}
        self.orders = {}
        
        # 风险管理
        self.max_position_size = 0.1  # 最大仓位比例
        self.max_daily_trades = 50
        self.daily_trade_count = 0
        
    async def __aenter__(self):
        await self.connector.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.connector.close()
    
    async def start_trading(self, strategy, symbols: List[str], 
                           capital_per_symbol: float = 500):
        """开始交易"""
        self.is_running = True
        self.logger.info(f"Starting trading with {len(symbols)} symbols")
        
        try:
            # 检查账户余额
            balances = await self.connector.get_balance()
            usdt_balance = balances.get('USDT', {}).get('free', 0)
            
            if usdt_balance < capital_per_symbol * len(symbols):
                raise ValueError(f"Insufficient balance. Required: {capital_per_symbol * len(symbols)}, Available: {usdt_balance}")
            
            # 为每个交易对分配资金
            for symbol in symbols:
                self.positions[symbol] = {
                    'allocated_capital': capital_per_symbol,
                    'current_position': 0,
                    'entry_price': 0,
                    'unrealized_pnl': 0
                }
            
            # 开始交易循环
            await self._trading_loop(strategy, symbols)
            
        except Exception as e:
            self.logger.error(f"Trading error: {e}")
            self.is_running = False
            raise
    
    async def _trading_loop(self, strategy, symbols: List[str]):
        """交易主循环"""
        while self.is_running:
            try:
                for symbol in symbols:
                    if self.daily_trade_count >= self.max_daily_trades:
                        self.logger.warning("Daily trade limit reached")
                        break
                    
                    await self._process_symbol(strategy, symbol)
                
                # 等待下一个周期
                await asyncio.sleep(60)  # 1分钟检查一次
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(30)
    
    async def _process_symbol(self, strategy, symbol: str):
        """处理单个交易对"""
        try:
            # 获取最新数据
            df = await self.connector.get_klines(symbol, '5m', limit=100)
            
            # 计算指标
            df = strategy.calculate_indicators(df)
            
            # 生成信号
            signals = strategy.generate_signals(df)
            current_signal = signals[-1] if signals else 'HOLD'
            
            # 获取当前价格
            current_price = await self.connector.get_symbol_price(symbol)
            
            # 执行交易逻辑
            await self._execute_trading_logic(symbol, current_signal, current_price, strategy)
            
        except Exception as e:
            self.logger.error(f"Error processing {symbol}: {e}")
    
    async def _execute_trading_logic(self, symbol: str, signal: str, 
                                   current_price: float, strategy):
        """执行交易逻辑"""
        position = self.positions.get(symbol, {})
        current_position = position.get('current_position', 0)
        
        try:
            if signal == 'BUY' and current_position <= 0:
                # 买入信号
                if current_position < 0:
                    # 先平空仓
                    await self._close_position(symbol, current_price)
                
                # 开多仓
                await self._open_long_position(symbol, current_price, strategy)
                
            elif signal == 'SELL' and current_position >= 0:
                # 卖出信号
                if current_position > 0:
                    # 先平多仓
                    await self._close_position(symbol, current_price)
                
                # 开空仓 (如果策略支持)
                if hasattr(strategy, 'enable_short') and strategy.enable_short:
                    await self._open_short_position(symbol, current_price, strategy)
            
            # 更新未实现盈亏
            await self._update_unrealized_pnl(symbol, current_price)
            
        except Exception as e:
            self.logger.error(f"Error executing trading logic for {symbol}: {e}")
    
    async def _open_long_position(self, symbol: str, price: float, strategy):
        """开多仓"""
        try:
            position = self.positions[symbol]
            capital = position['allocated_capital']
            
            # 计算仓位大小
            if hasattr(strategy, 'calculate_position_size'):
                quantity = strategy.calculate_position_size(capital, price, 0.02)  # 假设ATR
            else:
                quantity = (capital * 0.95) / price  # 95%资金利用率
            
            # 下单
            result = await self.connector.place_order(
                symbol=symbol,
                side='BUY',
                order_type='MARKET',
                quantity=quantity,
                test=True  # 测试模式
            )
            
            # 更新仓位
            position['current_position'] = quantity
            position['entry_price'] = price
            
            self.daily_trade_count += 1
            self.logger.info(f"Opened long position: {symbol} {quantity} @ {price}")
            
        except Exception as e:
            self.logger.error(f"Error opening long position for {symbol}: {e}")
    
    async def _open_short_position(self, symbol: str, price: float, strategy):
        """开空仓 (现货无法做空，这里仅作示例)"""
        self.logger.warning(f"Short selling not supported for spot trading: {symbol}")
    
    async def _close_position(self, symbol: str, price: float):
        """平仓"""
        try:
            position = self.positions[symbol]
            current_position = position['current_position']
            
            if current_position == 0:
                return
            
            # 计算盈亏
            entry_price = position['entry_price']
            pnl = current_position * (price - entry_price)
            
            # 下单平仓
            side = 'SELL' if current_position > 0 else 'BUY'
            result = await self.connector.place_order(
                symbol=symbol,
                side=side,
                order_type='MARKET',
                quantity=abs(current_position),
                test=True  # 测试模式
            )
            
            # 更新仓位
            position['current_position'] = 0
            position['entry_price'] = 0
            position['unrealized_pnl'] = 0
            
            self.daily_trade_count += 1
            self.logger.info(f"Closed position: {symbol} PnL: {pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error closing position for {symbol}: {e}")
    
    async def _update_unrealized_pnl(self, symbol: str, current_price: float):
        """更新未实现盈亏"""
        position = self.positions[symbol]
        current_position = position['current_position']
        
        if current_position != 0:
            entry_price = position['entry_price']
            unrealized_pnl = current_position * (current_price - entry_price)
            position['unrealized_pnl'] = unrealized_pnl
    
    async def get_portfolio_status(self) -> Dict:
        """获取投资组合状态"""
        total_allocated = sum(pos['allocated_capital'] for pos in self.positions.values())
        total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in self.positions.values())
        
        return {
            'total_allocated_capital': total_allocated,
            'total_unrealized_pnl': total_unrealized_pnl,
            'daily_trade_count': self.daily_trade_count,
            'positions': self.positions,
            'is_running': self.is_running
        }
    
    def stop_trading(self):
        """停止交易"""
        self.is_running = False
        self.logger.info("Trading stopped")


# 使用示例
async def main():
    """主函数示例"""
    api_key = "your_api_key_here"
    api_secret = "your_api_secret_here"
    
    async with BinanceConnector(api_key, api_secret, testnet=True) as connector:
        # 测试连接
        await connector.test_connectivity()
        
        # 获取账户信息
        account = await connector.get_account_info()
        print(f"Account info: {account}")
        
        # 获取价格
        btc_price = await connector.get_symbol_price('BTCUSDT')
        print(f"BTC price: {btc_price}")


if __name__ == "__main__":
    asyncio.run(main())
