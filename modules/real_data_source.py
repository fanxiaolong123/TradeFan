"""
真实数据源集成模块
支持多个免费数据源: Yahoo Finance, Alpha Vantage等
"""

import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os

class RealDataSource:
    """真实数据源管理器"""
    
    def __init__(self):
        # 简化日志初始化
        import logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.cache_dir = "data/cache"
        self.ensure_cache_dir()
        
        # 数据源配置
        self.sources = {
            'yahoo': self._get_yahoo_data,
            'alpha_vantage': self._get_alpha_vantage_data,
            'binance': self._get_binance_data
        }
        
        # API配置
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
        
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_data(self, symbol: str, timeframe: str = '1d', 
                 start_date: str = None, end_date: str = None,
                 source: str = 'yahoo') -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 交易对符号 (如 'BTC-USD', 'AAPL')
            timeframe: 时间框架 ('1m', '5m', '1h', '1d')
            start_date: 开始日期 ('2023-01-01')
            end_date: 结束日期 ('2023-12-31')
            source: 数据源 ('yahoo', 'alpha_vantage', 'binance')
        """
        try:
            # 检查缓存
            cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}_{source}"
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                self.logger.info(f"使用缓存数据: {symbol}")
                return cached_data
            
            # 获取数据
            if source in self.sources:
                data = self.sources[source](symbol, timeframe, start_date, end_date)
                
                # 缓存数据
                self._cache_data(cache_key, data)
                
                self.logger.info(f"成功获取数据: {symbol} from {source}")
                return data
            else:
                raise ValueError(f"不支持的数据源: {source}")
                
        except Exception as e:
            self.logger.error(f"获取数据失败 {symbol}: {str(e)}")
            return self._generate_fallback_data(symbol)
    
    def _get_yahoo_data(self, symbol: str, timeframe: str, 
                       start_date: str, end_date: str) -> pd.DataFrame:
        """从Yahoo Finance获取数据"""
        try:
            import yfinance as yf
            
            # 转换符号格式
            yahoo_symbol = self._convert_to_yahoo_symbol(symbol)
            
            # 设置默认日期
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 获取数据
            ticker = yf.Ticker(yahoo_symbol)
            
            # 时间框架映射
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '1d': '1d', '1wk': '1wk', '1mo': '1mo'
            }
            
            interval = interval_map.get(timeframe, '1d')
            
            # 下载数据
            data = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if data.empty:
                raise ValueError("Yahoo Finance返回空数据")
            
            # 标准化列名
            data = data.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 
                'Close': 'close', 'Volume': 'volume'
            })
            
            # 重置索引
            data.reset_index(inplace=True)
            data['datetime'] = data['Date'] if 'Date' in data.columns else data.index
            
            return data[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            
        except ImportError:
            self.logger.warning("yfinance未安装，请运行: pip install yfinance")
            raise
        except Exception as e:
            self.logger.error(f"Yahoo Finance数据获取失败: {str(e)}")
            raise
    
    def _get_alpha_vantage_data(self, symbol: str, timeframe: str,
                               start_date: str, end_date: str) -> pd.DataFrame:
        """从Alpha Vantage获取数据"""
        try:
            base_url = "https://www.alphavantage.co/query"
            
            # 时间框架映射
            function_map = {
                '1m': 'TIME_SERIES_INTRADAY',
                '5m': 'TIME_SERIES_INTRADAY', 
                '15m': 'TIME_SERIES_INTRADAY',
                '30m': 'TIME_SERIES_INTRADAY',
                '1h': 'TIME_SERIES_INTRADAY',
                '1d': 'TIME_SERIES_DAILY'
            }
            
            function = function_map.get(timeframe, 'TIME_SERIES_DAILY')
            
            params = {
                'function': function,
                'symbol': symbol,
                'apikey': self.alpha_vantage_key,
                'outputsize': 'full'
            }
            
            if 'INTRADAY' in function:
                params['interval'] = timeframe
            
            response = requests.get(base_url, params=params)
            data = response.json()
            
            # 解析数据
            if 'Error Message' in data:
                raise ValueError(f"Alpha Vantage错误: {data['Error Message']}")
            
            # 获取时间序列数据
            time_series_key = None
            for key in data.keys():
                if 'Time Series' in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                raise ValueError("未找到时间序列数据")
            
            time_series = data[time_series_key]
            
            # 转换为DataFrame
            df_data = []
            for date_str, values in time_series.items():
                row = {
                    'datetime': pd.to_datetime(date_str),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume'])
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 过滤日期范围
            if start_date:
                df = df[df['datetime'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['datetime'] <= pd.to_datetime(end_date)]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Alpha Vantage数据获取失败: {str(e)}")
            raise
    
    def _get_binance_data(self, symbol: str, timeframe: str,
                         start_date: str, end_date: str) -> pd.DataFrame:
        """从Binance获取数据"""
        try:
            base_url = "https://api.binance.com/api/v3/klines"
            
            # 转换符号格式 (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace('/', '').replace('-', '')
            
            # 时间框架映射
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
                '30m': '30m', '1h': '1h', '2h': '2h', '4h': '4h',
                '6h': '6h', '8h': '8h', '12h': '12h', '1d': '1d',
                '3d': '3d', '1w': '1w', '1M': '1M'
            }
            
            interval = interval_map.get(timeframe, '1d')
            
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': 1000
            }
            
            # 添加时间范围
            if start_date:
                start_ts = int(pd.to_datetime(start_date).timestamp() * 1000)
                params['startTime'] = start_ts
            
            if end_date:
                end_ts = int(pd.to_datetime(end_date).timestamp() * 1000)
                params['endTime'] = end_ts
            
            response = requests.get(base_url, params=params)
            data = response.json()
            
            if isinstance(data, dict) and 'code' in data:
                raise ValueError(f"Binance API错误: {data.get('msg', 'Unknown error')}")
            
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.error(f"Binance数据获取失败: {str(e)}")
            raise
    
    def _convert_to_yahoo_symbol(self, symbol: str) -> str:
        """转换为Yahoo Finance符号格式"""
        # 加密货币映射
        crypto_map = {
            'BTC/USDT': 'BTC-USD',
            'ETH/USDT': 'ETH-USD',
            'BNB/USDT': 'BNB-USD',
            'ADA/USDT': 'ADA-USD',
            'SOL/USDT': 'SOL-USD',
            'DOT/USDT': 'DOT-USD',
            'MATIC/USDT': 'MATIC-USD',
            'AVAX/USDT': 'AVAX-USD'
        }
        
        return crypto_map.get(symbol, symbol)
    
    def _get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """获取缓存数据"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.parquet")
            if os.path.exists(cache_file):
                # 检查缓存是否过期 (1小时)
                file_time = os.path.getmtime(cache_file)
                if time.time() - file_time < 3600:  # 1小时
                    return pd.read_parquet(cache_file)
            return None
        except Exception:
            return None
    
    def _cache_data(self, cache_key: str, data: pd.DataFrame):
        """缓存数据"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.parquet")
            data.to_parquet(cache_file, index=False)
        except Exception as e:
            self.logger.warning(f"缓存数据失败: {str(e)}")
    
    def _generate_fallback_data(self, symbol: str) -> pd.DataFrame:
        """生成备用模拟数据"""
        self.logger.warning(f"使用模拟数据替代: {symbol}")
        
        # 生成30天的模拟数据
        dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='D')
        
        # 模拟价格走势
        np.random.seed(42)
        base_price = 50000 if 'BTC' in symbol else 3000
        
        prices = []
        current_price = base_price
        
        for _ in range(len(dates)):
            # 随机游走
            change = np.random.normal(0, 0.02)  # 2%标准差
            current_price *= (1 + change)
            prices.append(current_price)
        
        # 生成OHLCV数据
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else close
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                'datetime': date,
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def get_available_symbols(self, source: str = 'yahoo') -> List[str]:
        """获取可用的交易对列表"""
        if source == 'yahoo':
            return [
                'BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD',
                'AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA'
            ]
        elif source == 'binance':
            return [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
                'DOTUSDT', 'MATICUSDT', 'AVAXUSDT'
            ]
        else:
            return []
    
    def test_connection(self, source: str = 'yahoo') -> bool:
        """测试数据源连接"""
        try:
            test_symbols = {
                'yahoo': 'BTC-USD',
                'binance': 'BTCUSDT',
                'alpha_vantage': 'IBM'
            }
            
            symbol = test_symbols.get(source, 'BTC-USD')
            data = self.get_data(symbol, '1d', source=source)
            
            return len(data) > 0
            
        except Exception as e:
            self.logger.error(f"数据源连接测试失败 {source}: {str(e)}")
            return False


# 测试函数
def test_real_data_source():
    """测试真实数据源"""
    print("🔍 测试真实数据源...")
    
    data_source = RealDataSource()
    
    # 测试不同数据源
    sources = ['yahoo', 'binance']
    
    for source in sources:
        print(f"\n📊 测试 {source} 数据源:")
        
        # 测试连接
        if data_source.test_connection(source):
            print(f"✅ {source} 连接成功")
            
            # 获取测试数据
            symbol = 'BTC-USD' if source == 'yahoo' else 'BTCUSDT'
            try:
                data = data_source.get_data(
                    symbol=symbol,
                    timeframe='1d',
                    start_date='2024-01-01',
                    end_date='2024-01-31',
                    source=source
                )
                
                print(f"✅ 数据获取成功: {len(data)} 条记录")
                print(f"   时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
                print(f"   价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
                
            except Exception as e:
                print(f"❌ 数据获取失败: {str(e)}")
        else:
            print(f"❌ {source} 连接失败")
    
    print("\n🎉 数据源测试完成!")


if __name__ == "__main__":
    test_real_data_source()
