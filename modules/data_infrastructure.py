"""
TradeFan 数据基础设施模块
支持 InfluxDB + Redis 高性能数据架构

实时数据流:
WebSocket → Redis缓存 → InfluxDB存储 → 查询API
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
    INFLUX_AVAILABLE = True
except ImportError:
    INFLUX_AVAILABLE = False
    logging.warning("InfluxDB client not available. Install with: pip install influxdb-client")

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis client not available. Install with: pip install redis")


class DataInfrastructureConfig:
    """数据基础设施配置"""
    
    def __init__(self):
        # InfluxDB 配置
        self.influx_url = "http://localhost:8086"
        self.influx_token = "your-token-here"
        self.influx_org = "tradefan"
        self.influx_bucket = "market_data"
        
        # Redis 配置
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 0
        self.redis_password = None
        
        # 性能配置
        self.batch_size = 1000
        self.flush_interval = 1.0  # 秒
        self.cache_ttl = 300  # Redis缓存TTL (秒)
        self.max_retries = 3


class InfluxDataWriter:
    """InfluxDB 高性能数据写入器"""
    
    def __init__(self, config: DataInfrastructureConfig):
        self.config = config
        self.client = None
        self.write_api = None
        self.buffer = []
        self.last_flush = datetime.now()
        self.logger = logging.getLogger(__name__)
        
        if INFLUX_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化InfluxDB客户端"""
        try:
            self.client = InfluxDBClient(
                url=self.config.influx_url,
                token=self.config.influx_token,
                org=self.config.influx_org
            )
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.logger.info("InfluxDB client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize InfluxDB client: {e}")
    
    async def write_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any], 
                               exchange: str = "binance"):
        """写入市场数据"""
        if not INFLUX_AVAILABLE or not self.client:
            self.logger.warning("InfluxDB not available, skipping write")
            return
        
        try:
            # 创建数据点
            point = Point("market_data") \
                .tag("symbol", symbol) \
                .tag("exchange", exchange) \
                .tag("timeframe", timeframe) \
                .field("open", float(data.get("open", 0))) \
                .field("high", float(data.get("high", 0))) \
                .field("low", float(data.get("low", 0))) \
                .field("close", float(data.get("close", 0))) \
                .field("volume", float(data.get("volume", 0))) \
                .time(data.get("timestamp", datetime.now(timezone.utc)))
            
            # 添加到缓冲区
            self.buffer.append(point)
            
            # 检查是否需要刷新
            if (len(self.buffer) >= self.config.batch_size or 
                (datetime.now() - self.last_flush).total_seconds() >= self.config.flush_interval):
                await self.flush_buffer()
                
        except Exception as e:
            self.logger.error(f"Error writing market data: {e}")
    
    async def write_indicator_data(self, symbol: str, timeframe: str, indicators: Dict[str, float],
                                  timestamp: Optional[datetime] = None):
        """写入技术指标数据"""
        if not INFLUX_AVAILABLE or not self.client:
            return
        
        try:
            point = Point("indicators") \
                .tag("symbol", symbol) \
                .tag("timeframe", timeframe) \
                .time(timestamp or datetime.now(timezone.utc))
            
            # 添加所有指标字段
            for indicator_name, value in indicators.items():
                if value is not None and not np.isnan(value):
                    point = point.field(indicator_name, float(value))
            
            self.buffer.append(point)
            
            if len(self.buffer) >= self.config.batch_size:
                await self.flush_buffer()
                
        except Exception as e:
            self.logger.error(f"Error writing indicator data: {e}")
    
    async def flush_buffer(self):
        """批量提交缓冲区数据"""
        if not self.buffer or not self.write_api:
            return
        
        try:
            # 批量写入
            self.write_api.write(
                bucket=self.config.influx_bucket,
                org=self.config.influx_org,
                record=self.buffer
            )
            
            self.logger.debug(f"Flushed {len(self.buffer)} points to InfluxDB")
            self.buffer.clear()
            self.last_flush = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error flushing buffer: {e}")
    
    async def close(self):
        """关闭连接"""
        if self.buffer:
            await self.flush_buffer()
        if self.client:
            self.client.close()


class RedisCache:
    """Redis 高性能缓存层"""
    
    def __init__(self, config: DataInfrastructureConfig):
        self.config = config
        self.redis_client = None
        self.logger = logging.getLogger(__name__)
        
        if REDIS_AVAILABLE:
            asyncio.create_task(self._initialize_client())
    
    async def _initialize_client(self):
        """初始化Redis客户端"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True
            )
            await self.redis_client.ping()
            self.logger.info("Redis client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis client: {e}")
    
    async def cache_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """缓存市场数据"""
        if not self.redis_client:
            return
        
        try:
            key = f"market:{symbol}:{timeframe}:latest"
            await self.redis_client.setex(
                key, 
                self.config.cache_ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            self.logger.error(f"Error caching market data: {e}")
    
    async def get_cached_market_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """获取缓存的市场数据"""
        if not self.redis_client:
            return None
        
        try:
            key = f"market:{symbol}:{timeframe}:latest"
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            self.logger.error(f"Error getting cached market data: {e}")
            return None
    
    async def cache_indicators(self, symbol: str, timeframe: str, indicators: Dict[str, float]):
        """缓存技术指标"""
        if not self.redis_client:
            return
        
        try:
            key = f"indicators:{symbol}:{timeframe}:latest"
            await self.redis_client.setex(
                key,
                self.config.cache_ttl,
                json.dumps(indicators, default=str)
            )
        except Exception as e:
            self.logger.error(f"Error caching indicators: {e}")
    
    async def get_cached_indicators(self, symbol: str, timeframe: str) -> Optional[Dict[str, float]]:
        """获取缓存的技术指标"""
        if not self.redis_client:
            return None
        
        try:
            key = f"indicators:{symbol}:{timeframe}:latest"
            data = await self.redis_client.get(key)
            if data:
                indicators = json.loads(data)
                # 转换为float类型
                return {k: float(v) for k, v in indicators.items() if v is not None}
            return None
        except Exception as e:
            self.logger.error(f"Error getting cached indicators: {e}")
            return None
    
    async def close(self):
        """关闭连接"""
        if self.redis_client:
            await self.redis_client.close()


class DataQueryAPI:
    """数据查询API"""
    
    def __init__(self, config: DataInfrastructureConfig):
        self.config = config
        self.client = None
        self.query_api = None
        self.logger = logging.getLogger(__name__)
        
        if INFLUX_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """初始化查询客户端"""
        try:
            self.client = InfluxDBClient(
                url=self.config.influx_url,
                token=self.config.influx_token,
                org=self.config.influx_org
            )
            self.query_api = self.client.query_api()
            self.logger.info("InfluxDB query client initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize query client: {e}")
    
    async def get_market_data(self, symbol: str, timeframe: str, 
                             start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """查询市场数据"""
        if not self.query_api:
            return pd.DataFrame()
        
        try:
            query = f'''
            from(bucket: "{self.config.influx_bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "market_data")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query)
            
            if not result.empty:
                # 清理和格式化数据
                result = result.drop(columns=['result', 'table', '_start', '_stop', '_measurement'], errors='ignore')
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                result = result.sort_index()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying market data: {e}")
            return pd.DataFrame()
    
    async def get_indicators(self, symbol: str, timeframe: str,
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """查询技术指标数据"""
        if not self.query_api:
            return pd.DataFrame()
        
        try:
            query = f'''
            from(bucket: "{self.config.influx_bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "indicators")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query)
            
            if not result.empty:
                result = result.drop(columns=['result', 'table', '_start', '_stop', '_measurement'], errors='ignore')
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                result = result.sort_index()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying indicators: {e}")
            return pd.DataFrame()
    
    async def get_latest_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """获取最新数据"""
        if not self.query_api:
            return pd.DataFrame()
        
        try:
            query = f'''
            from(bucket: "{self.config.influx_bucket}")
                |> range(start: -24h)
                |> filter(fn: (r) => r["_measurement"] == "market_data")
                |> filter(fn: (r) => r["symbol"] == "{symbol}")
                |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: {limit})
            '''
            
            result = self.query_api.query_data_frame(query)
            
            if not result.empty:
                result = result.drop(columns=['result', 'table', '_start', '_stop', '_measurement'], errors='ignore')
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                result = result.sort_index()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying latest data: {e}")
            return pd.DataFrame()


class DataInfrastructureManager:
    """数据基础设施管理器"""
    
    def __init__(self, config: Optional[DataInfrastructureConfig] = None):
        self.config = config or DataInfrastructureConfig()
        self.writer = InfluxDataWriter(self.config)
        self.cache = RedisCache(self.config)
        self.query_api = DataQueryAPI(self.config)
        self.logger = logging.getLogger(__name__)
    
    async def store_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """存储市场数据（缓存+持久化）"""
        # 同时写入缓存和数据库
        await asyncio.gather(
            self.cache.cache_market_data(symbol, timeframe, data),
            self.writer.write_market_data(symbol, timeframe, data),
            return_exceptions=True
        )
    
    async def store_indicators(self, symbol: str, timeframe: str, indicators: Dict[str, float]):
        """存储技术指标数据"""
        await asyncio.gather(
            self.cache.cache_indicators(symbol, timeframe, indicators),
            self.writer.write_indicator_data(symbol, timeframe, indicators),
            return_exceptions=True
        )
    
    async def get_market_data(self, symbol: str, timeframe: str, 
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             use_cache: bool = True) -> pd.DataFrame:
        """获取市场数据"""
        # 如果没有指定时间范围，尝试从缓存获取最新数据
        if not start_time and not end_time and use_cache:
            cached_data = await self.cache.get_cached_market_data(symbol, timeframe)
            if cached_data:
                return pd.DataFrame([cached_data])
        
        # 从数据库查询
        if start_time and end_time:
            return await self.query_api.get_market_data(symbol, timeframe, start_time, end_time)
        else:
            return await self.query_api.get_latest_data(symbol, timeframe)
    
    async def get_indicators(self, symbol: str, timeframe: str,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           use_cache: bool = True) -> Dict[str, float]:
        """获取技术指标"""
        # 尝试从缓存获取
        if use_cache and not start_time and not end_time:
            cached_indicators = await self.cache.get_cached_indicators(symbol, timeframe)
            if cached_indicators:
                return cached_indicators
        
        # 从数据库查询
        if start_time and end_time:
            df = await self.query_api.get_indicators(symbol, timeframe, start_time, end_time)
            if not df.empty:
                return df.iloc[-1].to_dict()  # 返回最新的指标值
        
        return {}
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        health_status = {
            "influxdb": False,
            "redis": False
        }
        
        try:
            # 检查InfluxDB
            if self.writer.client:
                health = self.writer.client.health()
                health_status["influxdb"] = health.status == "pass"
        except Exception as e:
            self.logger.error(f"InfluxDB health check failed: {e}")
        
        try:
            # 检查Redis
            if self.cache.redis_client:
                await self.cache.redis_client.ping()
                health_status["redis"] = True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
        
        return health_status
    
    async def close(self):
        """关闭所有连接"""
        await asyncio.gather(
            self.writer.close(),
            self.cache.close(),
            return_exceptions=True
        )


# 全局实例
data_infrastructure = None

def get_data_infrastructure() -> DataInfrastructureManager:
    """获取数据基础设施实例"""
    global data_infrastructure
    if data_infrastructure is None:
        data_infrastructure = DataInfrastructureManager()
    return data_infrastructure


# 使用示例
async def example_usage():
    """使用示例"""
    # 初始化数据基础设施
    infra = get_data_infrastructure()
    
    # 存储市场数据
    market_data = {
        "open": 45000.0,
        "high": 45100.0,
        "low": 44900.0,
        "close": 45050.0,
        "volume": 1234.56,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await infra.store_market_data("BTC/USDT", "1m", market_data)
    
    # 存储技术指标
    indicators = {
        "ema_fast": 45025.0,
        "ema_slow": 44980.0,
        "rsi": 65.5,
        "macd": 12.3,
        "bb_upper": 45200.0,
        "bb_lower": 44800.0
    }
    
    await infra.store_indicators("BTC/USDT", "1m", indicators)
    
    # 查询数据
    df = await infra.get_market_data("BTC/USDT", "1m")
    print(f"Retrieved {len(df)} market data points")
    
    cached_indicators = await infra.get_indicators("BTC/USDT", "1m")
    print(f"Retrieved indicators: {cached_indicators}")
    
    # 健康检查
    health = await infra.health_check()
    print(f"Health status: {health}")
    
    # 关闭连接
    await infra.close()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
