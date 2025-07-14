"""
统一API客户端
封装所有交易所API调用，包括签名生成、请求发送、错误处理
支持多个交易所：Binance、OKX等
"""

import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json


class APIClient:
    """统一的交易所API客户端"""
    
    def __init__(self, exchange: str, api_key: str, api_secret: str, 
                 base_url: str, testnet: bool = True, logger: Optional[logging.Logger] = None):
        """
        初始化API客户端
        
        Args:
            exchange: 交易所名称 ('binance', 'okx', etc.)
            api_key: API密钥
            api_secret: API密钥
            base_url: API基础URL
            testnet: 是否使用测试网
            logger: 日志记录器
        """
        self.exchange = exchange.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.testnet = testnet
        self.logger = logger or logging.getLogger(__name__)
        
        # 请求限制设置
        self.request_timeout = 10
        self.max_retries = 3
        self.retry_delay = 1
        
        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
        
        self.logger.info(f"🔗 初始化{exchange}API客户端 (测试网: {testnet})")
    
    def _generate_signature(self, query_string: str) -> str:
        """
        生成API签名
        
        Args:
            query_string: 查询字符串
            
        Returns:
            签名字符串
        """
        if self.exchange == 'binance':
            return hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        elif self.exchange == 'okx':
            # OKX使用不同的签名方式
            timestamp = str(int(time.time()))
            message = timestamp + 'GET' + '/api/v5/' + query_string
            return hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest().hex()
        else:
            raise ValueError(f"不支持的交易所: {self.exchange}")
    
    def _prepare_headers(self, signed: bool = False) -> Dict[str, str]:
        """
        准备请求头
        
        Args:
            signed: 是否需要签名
            
        Returns:
            请求头字典
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TradeFan/2.0.0'
        }
        
        if self.exchange == 'binance':
            headers['X-MBX-APIKEY'] = self.api_key
        elif self.exchange == 'okx':
            headers['OK-ACCESS-KEY'] = self.api_key
            if signed:
                timestamp = str(int(time.time()))
                headers['OK-ACCESS-TIMESTAMP'] = timestamp
                headers['OK-ACCESS-PASSPHRASE'] = 'your_passphrase'  # 需要配置
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     signed: bool = False, retries: int = 0) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            method: HTTP方法 ('GET', 'POST', 'DELETE')
            endpoint: API端点
            params: 请求参数
            signed: 是否需要签名
            retries: 重试次数
            
        Returns:
            响应数据
        """
        if params is None:
            params = {}
        
        # 添加时间戳（如果需要签名）
        if signed:
            params['timestamp'] = int(time.time() * 1000)
        
        # 生成查询字符串和签名
        query_string = urlencode(params) if params else ''
        if signed and query_string:
            signature = self._generate_signature(query_string)
            params['signature'] = signature
            query_string = urlencode(params)
        
        # 构建完整URL
        url = f"{self.base_url}{endpoint}"
        if method == 'GET' and query_string:
            url += f"?{query_string}"
        
        # 准备请求头
        headers = self._prepare_headers(signed)
        
        # 请求限制检查
        current_time = time.time()
        if current_time - self.last_request_time < 0.1:  # 100ms限制
            time.sleep(0.1)
        
        try:
            self.logger.debug(f"📡 API请求: {method} {endpoint}")
            
            # 发送请求
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=self.request_timeout)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params if method == 'POST' else None, 
                                       timeout=self.request_timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=self.request_timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            self.last_request_time = time.time()
            self.request_count += 1
            
            # 检查响应状态
            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"✅ API响应成功: {endpoint}")
                return data
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                self.error_count += 1
                
                # 重试逻辑
                if retries < self.max_retries and response.status_code in [429, 500, 502, 503, 504]:
                    self.logger.warning(f"🔄 重试请求 ({retries + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay * (retries + 1))
                    return self._make_request(method, endpoint, params, signed, retries + 1)
                
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求异常: {str(e)}"
            self.logger.error(error_msg)
            self.error_count += 1
            
            # 重试逻辑
            if retries < self.max_retries:
                self.logger.warning(f"🔄 重试请求 ({retries + 1}/{self.max_retries})")
                time.sleep(self.retry_delay * (retries + 1))
                return self._make_request(method, endpoint, params, signed, retries + 1)
            
            raise Exception(error_msg)
    
    # ==================== 账户相关API ====================
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/account', signed=True)
        elif self.exchange == 'okx':
            return self._make_request('GET', '/api/v5/account/balance', signed=True)
    
    def get_balance(self, asset: str = None) -> Dict[str, Any]:
        """
        获取余额信息
        
        Args:
            asset: 资产名称，如果为None则返回所有资产
            
        Returns:
            余额信息
        """
        account_info = self.get_account_info()
        
        if self.exchange == 'binance':
            balances = account_info.get('balances', [])
            if asset:
                for balance in balances:
                    if balance['asset'] == asset.upper():
                        return {
                            'asset': balance['asset'],
                            'free': float(balance['free']),
                            'locked': float(balance['locked']),
                            'total': float(balance['free']) + float(balance['locked'])
                        }
                return {'asset': asset.upper(), 'free': 0.0, 'locked': 0.0, 'total': 0.0}
            else:
                return {b['asset']: {
                    'free': float(b['free']),
                    'locked': float(b['locked']),
                    'total': float(b['free']) + float(b['locked'])
                } for b in balances if float(b['free']) > 0 or float(b['locked']) > 0}
    
    # ==================== 市场数据API ====================
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取交易对价格信息"""
        params = {'symbol': symbol.upper()}
        
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/ticker/24hr', params)
        elif self.exchange == 'okx':
            return self._make_request('GET', '/api/v5/market/ticker', params)
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500, 
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[List]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对
            interval: 时间间隔 ('1m', '5m', '1h', '1d', etc.)
            limit: 数据条数
            start_time: 开始时间戳
            end_time: 结束时间戳
            
        Returns:
            K线数据列表
        """
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'limit': min(limit, 1000)  # 限制最大请求数量
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/klines', params)
        elif self.exchange == 'okx':
            # OKX使用不同的参数名
            params['instId'] = params.pop('symbol')
            params['bar'] = params.pop('interval')
            return self._make_request('GET', '/api/v5/market/candles', params)
    
    # ==================== 交易相关API ====================
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float,
                   price: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        """
        下单
        
        Args:
            symbol: 交易对
            side: 买卖方向 ('BUY', 'SELL')
            order_type: 订单类型 ('MARKET', 'LIMIT', 'STOP_LOSS', etc.)
            quantity: 数量
            price: 价格（限价单需要）
            **kwargs: 其他参数
            
        Returns:
            订单信息
        """
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity
        }
        
        if price and order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
            params['price'] = price
        
        # 添加其他参数
        params.update(kwargs)
        
        self.logger.info(f"📝 下单: {side} {quantity} {symbol} @ {price or 'MARKET'}")
        
        if self.exchange == 'binance':
            return self._make_request('POST', '/api/v3/order', params, signed=True)
        elif self.exchange == 'okx':
            # OKX参数转换
            okx_params = {
                'instId': params['symbol'],
                'tdMode': 'cash',
                'side': params['side'].lower(),
                'ordType': 'market' if params['type'] == 'MARKET' else 'limit',
                'sz': str(params['quantity'])
            }
            if price:
                okx_params['px'] = str(price)
            return self._make_request('POST', '/api/v5/trade/order', okx_params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        
        self.logger.info(f"❌ 取消订单: {order_id}")
        
        if self.exchange == 'binance':
            return self._make_request('DELETE', '/api/v3/order', params, signed=True)
        elif self.exchange == 'okx':
            return self._make_request('POST', '/api/v5/trade/cancel-order', params, signed=True)
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """查询订单状态"""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/order', params, signed=True)
        elif self.exchange == 'okx':
            return self._make_request('GET', '/api/v5/trade/order', params, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/openOrders', params, signed=True)
        elif self.exchange == 'okx':
            return self._make_request('GET', '/api/v5/trade/orders-pending', params, signed=True)
    
    # ==================== 工具方法 ====================
    
    def test_connectivity(self) -> bool:
        """测试API连接"""
        try:
            if self.exchange == 'binance':
                response = self._make_request('GET', '/api/v3/ping')
                return response == {}
            elif self.exchange == 'okx':
                response = self._make_request('GET', '/api/v5/public/time')
                return 'data' in response
            return False
        except Exception as e:
            self.logger.error(f"❌ API连接测试失败: {e}")
            return False
    
    def get_server_time(self) -> int:
        """获取服务器时间"""
        if self.exchange == 'binance':
            response = self._make_request('GET', '/api/v3/time')
            return response.get('serverTime', 0)
        elif self.exchange == 'okx':
            response = self._make_request('GET', '/api/v5/public/time')
            return int(response.get('data', [{}])[0].get('ts', 0))
    
    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """获取交易所信息"""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        
        if self.exchange == 'binance':
            return self._make_request('GET', '/api/v3/exchangeInfo', params)
        elif self.exchange == 'okx':
            return self._make_request('GET', '/api/v5/public/instruments', {'instType': 'SPOT'})
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取API使用统计"""
        return {
            'exchange': self.exchange,
            'testnet': self.testnet,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_request_time': datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time else None
        }
    
    def __str__(self):
        return f"APIClient({self.exchange}, testnet={self.testnet})"
    
    def __repr__(self):
        return self.__str__()
