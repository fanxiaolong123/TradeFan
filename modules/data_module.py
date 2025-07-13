"""
数据模块
负责从交易所获取行情数据、K线数据等
集成多个数据源: Yahoo Finance, Binance, Alpha Vantage
"""

import ccxt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime, timedelta
import os
import pickle
from .real_data_source import RealDataSource

class DataModule:
    """数据获取和管理模块"""
    
    def __init__(self, config: Dict, logger=None):
        self.config = config
        self.logger = logger
        self.exchange = self._init_exchange()
        self.data_cache = {}
        self.cache_dir = "data/cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化真实数据源
        self.real_data_source = RealDataSource()
        
        # 数据源优先级
        self.data_source_priority = ['yahoo', 'binance', 'fallback']
    
    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            exchange_config = self.config.get('exchange', {})
            exchange_class = getattr(ccxt, exchange_config.get('name', 'binance'))
            
            exchange = exchange_class({
                'apiKey': exchange_config.get('api_key', ''),
                'secret': exchange_config.get('secret', ''),
                'sandbox': exchange_config.get('sandbox', True),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # 现货交易
                }
            })
            
            if self.logger:
                self.logger.info(f"交易所连接初始化成功: {exchange_config.get('name', 'binance')}")
            
            return exchange
            
        except Exception as e:
            error_msg = f"交易所连接初始化失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 500, 
                  start_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        获取OHLCV数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 数据条数
            start_time: 开始时间
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            # 检查缓存
            cache_key = f"{symbol}_{timeframe}_{limit}"
            if cache_key in self.data_cache:
                cached_data, cache_time = self.data_cache[cache_key]
                # 如果缓存时间小于5分钟，直接返回缓存数据
                if (datetime.now() - cache_time).seconds < 300:
                    return cached_data
            
            # 获取数据
            since = None
            if start_time:
                since = int(start_time.timestamp() * 1000)
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            # 转换为DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 确保数据类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 缓存数据
            self.data_cache[cache_key] = (df.copy(), datetime.now())
            
            if self.logger:
                self.logger.debug(f"获取{symbol} {timeframe}数据成功，共{len(df)}条记录")
            
            return df
            
        except Exception as e:
            error_msg = f"获取{symbol}数据失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_ticker(self, symbol: str) -> Dict:
        """获取实时价格信息"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'timestamp': pd.Timestamp.now()
            }
        except Exception as e:
            error_msg = f"获取{symbol}实时价格失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """获取订单簿数据"""
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            return {
                'symbol': symbol,
                'bids': order_book['bids'],
                'asks': order_book['asks'],
                'timestamp': pd.Timestamp.now()
            }
        except Exception as e:
            error_msg = f"获取{symbol}订单簿失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_historical_data(self, symbol: str, timeframe: str, 
                          start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取历史数据（用于回测）
        优先使用真实数据源，失败时回退到模拟数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            历史OHLCV数据
        """
        # 尝试使用真实数据源
        for source in self.data_source_priority:
            try:
                if source == 'fallback':
                    # 使用原有的模拟数据生成逻辑
                    return self._generate_fallback_data(symbol, start_date, end_date)
                
                if self.logger:
                    self.logger.info(f"尝试从{source}获取{symbol}历史数据")
                
                # 使用真实数据源
                data = self.real_data_source.get_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    source=source
                )
                
                if len(data) > 0:
                    # 转换为标准格式
                    df = data.copy()
                    df.set_index('datetime', inplace=True)
                    df = df[~df.index.duplicated(keep='first')].sort_index()
                    
                    if self.logger:
                        self.logger.info(f"成功从{source}获取{symbol}数据: {len(df)}条记录")
                    
                    return df
                    
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"从{source}获取{symbol}数据失败: {str(e)}")
                continue
        
        # 所有数据源都失败，抛出异常
        error_msg = f"获取{symbol}历史数据失败: 所有数据源都不可用"
        if self.logger:
            self.logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_account_balance(self) -> Dict:
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'total': balance['total'],
                'free': balance['free'],
                'used': balance['used'],
                'timestamp': pd.Timestamp.now()
            }
        except Exception as e:
            error_msg = f"获取账户余额失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            return {}
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证交易对是否有效"""
        try:
            markets = self.exchange.load_markets()
            return symbol in markets
        except Exception as e:
            if self.logger:
                self.logger.error(f"验证交易对{symbol}失败: {e}")
            return False
    
    def get_market_info(self, symbol: str) -> Dict:
        """获取市场信息"""
        try:
            markets = self.exchange.load_markets()
            if symbol in markets:
                market = markets[symbol]
                return {
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'min_amount': market['limits']['amount']['min'],
                    'max_amount': market['limits']['amount']['max'],
                    'min_price': market['limits']['price']['min'],
                    'max_price': market['limits']['price']['max'],
                    'precision_amount': market['precision']['amount'],
                    'precision_price': market['precision']['price']
                }
            else:
                raise Exception(f"交易对{symbol}不存在")
        except Exception as e:
            error_msg = f"获取{symbol}市场信息失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def clear_cache(self):
        """清除数据缓存"""
        self.data_cache.clear()
        if self.logger:
            self.logger.info("数据缓存已清除")
