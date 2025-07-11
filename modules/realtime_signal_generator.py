"""
实时信号生成器
Real-time Signal Generator

支持WebSocket实时数据流，异步信号生成和处理
专为短线交易优化，提供毫秒级响应
"""

import asyncio
import websockets
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from collections import deque
import threading
import time
from queue import Queue, Empty

@dataclass
class RealTimeSignal:
    """实时信号数据结构"""
    symbol: str
    timeframe: str
    timestamp: datetime
    signal_type: int  # 1: 买入, -1: 卖出, 0: 无信号
    signal_strength: float  # 0-1
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str
    confidence: float
    risk_level: str
    metadata: Dict[str, Any]

@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str

class RealTimeDataBuffer:
    """实时数据缓冲区"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffers = {}  # {symbol_timeframe: deque}
        self.lock = threading.Lock()
    
    def add_data(self, symbol: str, timeframe: str, data: MarketData):
        """添加数据到缓冲区"""
        key = f"{symbol}_{timeframe}"
        
        with self.lock:
            if key not in self.buffers:
                self.buffers[key] = deque(maxlen=self.max_size)
            
            self.buffers[key].append(data)
    
    def get_data(self, symbol: str, timeframe: str, count: int = None) -> List[MarketData]:
        """获取缓冲区数据"""
        key = f"{symbol}_{timeframe}"
        
        with self.lock:
            if key not in self.buffers:
                return []
            
            buffer = self.buffers[key]
            if count is None:
                return list(buffer)
            else:
                return list(buffer)[-count:] if len(buffer) >= count else list(buffer)
    
    def to_dataframe(self, symbol: str, timeframe: str, count: int = None) -> pd.DataFrame:
        """转换为DataFrame"""
        data_list = self.get_data(symbol, timeframe, count)
        
        if not data_list:
            return pd.DataFrame()
        
        df_data = []
        for data in data_list:
            df_data.append({
                'timestamp': data.timestamp,
                'open': data.open,
                'high': data.high,
                'low': data.low,
                'close': data.close,
                'volume': data.volume
            })
        
        df = pd.DataFrame(df_data)
        df.set_index('timestamp', inplace=True)
        return df

class RealTimeSignalGenerator:
    """实时信号生成器"""
    
    def __init__(self, strategies: Dict[str, Any] = None):
        """
        初始化实时信号生成器
        
        Args:
            strategies: 策略字典 {strategy_name: strategy_instance}
        """
        self.strategies = strategies or {}
        self.data_buffer = RealTimeDataBuffer()
        self.signal_queue = Queue()
        self.active_monitors = {}
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # WebSocket连接管理
        self.ws_connections = {}
        self.ws_callbacks = {}
        
        # 信号处理配置
        self.signal_config = {
            'min_signal_interval': 60,  # 最小信号间隔(秒)
            'max_signals_per_hour': 10,  # 每小时最大信号数
            'signal_expiry': 300,       # 信号过期时间(秒)
        }
        
        # 信号历史记录
        self.signal_history = deque(maxlen=1000)
        self.last_signals = {}  # {symbol: timestamp}
        
        # 性能监控
        self.performance_stats = {
            'signals_generated': 0,
            'signals_processed': 0,
            'avg_processing_time': 0,
            'last_update': datetime.now()
        }
    
    async def start_monitoring(self, symbols: List[str], timeframes: List[str]):
        """
        开始监控指定的交易对和时间框架
        
        Args:
            symbols: 交易对列表
            timeframes: 时间框架列表
        """
        self.running = True
        self.logger.info(f"开始监控 {len(symbols)} 个交易对，{len(timeframes)} 个时间框架")
        
        # 创建监控任务
        tasks = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                task = asyncio.create_task(
                    self._monitor_symbol_timeframe(symbol, timeframe)
                )
                tasks.append(task)
                
                key = f"{symbol}_{timeframe}"
                self.active_monitors[key] = task
        
        # 启动信号处理任务
        signal_task = asyncio.create_task(self._process_signals())
        tasks.append(signal_task)
        
        # 启动WebSocket数据流
        ws_task = asyncio.create_task(self._start_websocket_streams(symbols, timeframes))
        tasks.append(ws_task)
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"监控任务异常: {e}")
        finally:
            self.running = False
    
    async def _monitor_symbol_timeframe(self, symbol: str, timeframe: str):
        """监控单个交易对和时间框架"""
        while self.running:
            try:
                # 获取最新数据
                df = self.data_buffer.to_dataframe(symbol, timeframe, 200)
                
                if len(df) < 50:  # 数据不足
                    await asyncio.sleep(1)
                    continue
                
                # 生成信号
                signals = await self._generate_signals(symbol, timeframe, df)
                
                # 将信号加入队列
                for signal in signals:
                    if self._validate_signal(signal):
                        self.signal_queue.put(signal)
                
                # 等待下一次检查
                await asyncio.sleep(self._get_check_interval(timeframe))
                
            except Exception as e:
                self.logger.error(f"监控 {symbol}_{timeframe} 异常: {e}")
                await asyncio.sleep(5)
    
    async def _generate_signals(self, symbol: str, timeframe: str, df: pd.DataFrame) -> List[RealTimeSignal]:
        """生成交易信号"""
        signals = []
        start_time = time.time()
        
        try:
            for strategy_name, strategy in self.strategies.items():
                # 计算指标
                df_with_indicators = strategy.calculate_indicators(df)
                
                # 生成信号
                df_with_signals = strategy.generate_signals(df_with_indicators)
                
                # 检查最新信号
                latest_signal = df_with_signals['signal'].iloc[-1]
                
                if latest_signal != 0:
                    # 创建信号对象
                    signal = self._create_signal(
                        symbol, timeframe, strategy_name, 
                        latest_signal, df_with_signals, strategy
                    )
                    
                    if signal:
                        signals.append(signal)
            
            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time)
            
        except Exception as e:
            self.logger.error(f"生成信号异常 {symbol}_{timeframe}: {e}")
        
        return signals
    
    def _create_signal(self, symbol: str, timeframe: str, strategy_name: str,
                      signal_type: int, df: pd.DataFrame, strategy) -> Optional[RealTimeSignal]:
        """创建信号对象"""
        try:
            latest_data = df.iloc[-1]
            current_price = latest_data['close']
            
            # 计算止损止盈
            if hasattr(strategy, '_calculate_dynamic_stops'):
                stop_loss = latest_data.get('dynamic_stop_loss', 0)
                take_profit = latest_data.get('dynamic_take_profit', 0)
            else:
                # 默认止损止盈计算
                atr = latest_data.get('atr', current_price * 0.02)
                if signal_type == 1:  # 买入
                    stop_loss = current_price - (atr * 2)
                    take_profit = current_price + (atr * 4)
                else:  # 卖出
                    stop_loss = current_price + (atr * 2)
                    take_profit = current_price - (atr * 4)
            
            # 获取信号强度
            signal_strength = strategy.get_signal_strength(df, -1)
            
            # 获取入场原因
            entry_reason = latest_data.get('entry_reason', f'{strategy_name}信号')
            
            # 计算信心度
            confidence = self._calculate_confidence(df, signal_type, signal_strength)
            
            # 风险等级
            risk_level = self._assess_risk_level(df, signal_type, confidence)
            
            signal = RealTimeSignal(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                signal_type=signal_type,
                signal_strength=signal_strength,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=entry_reason,
                confidence=confidence,
                risk_level=risk_level,
                metadata={
                    'strategy': strategy_name,
                    'atr': latest_data.get('atr', 0),
                    'rsi': latest_data.get('rsi', 0),
                    'volume_ratio': latest_data.get('volume_ratio', 1),
                    'trend_strength': latest_data.get('trend_strength', 0)
                }
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"创建信号失败: {e}")
            return None
    
    def _validate_signal(self, signal: RealTimeSignal) -> bool:
        """验证信号有效性"""
        # 检查信号间隔
        key = f"{signal.symbol}_{signal.timeframe}"
        if key in self.last_signals:
            time_diff = (signal.timestamp - self.last_signals[key]).total_seconds()
            if time_diff < self.signal_config['min_signal_interval']:
                return False
        
        # 检查每小时信号数量
        hour_ago = signal.timestamp - timedelta(hours=1)
        recent_signals = [
            s for s in self.signal_history 
            if s.symbol == signal.symbol and s.timestamp > hour_ago
        ]
        
        if len(recent_signals) >= self.signal_config['max_signals_per_hour']:
            return False
        
        # 检查信号质量
        if signal.confidence < 0.3:  # 信心度太低
            return False
        
        if signal.signal_strength < 0.5:  # 信号强度太弱
            return False
        
        return True
    
    async def _process_signals(self):
        """处理信号队列"""
        while self.running:
            try:
                # 从队列获取信号
                try:
                    signal = self.signal_queue.get(timeout=1)
                except Empty:
                    continue
                
                # 处理信号
                await self._handle_signal(signal)
                
                # 记录信号
                self.signal_history.append(signal)
                self.last_signals[f"{signal.symbol}_{signal.timeframe}"] = signal.timestamp
                
                # 更新统计
                self.performance_stats['signals_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"处理信号异常: {e}")
                await asyncio.sleep(1)
    
    async def _handle_signal(self, signal: RealTimeSignal):
        """处理单个信号"""
        self.logger.info(f"处理信号: {signal.symbol} {signal.timeframe} "
                        f"{'买入' if signal.signal_type == 1 else '卖出'} "
                        f"价格: {signal.entry_price:.4f} "
                        f"信心度: {signal.confidence:.2f}")
        
        # 这里可以添加信号处理逻辑，如：
        # 1. 发送通知
        # 2. 执行交易
        # 3. 记录日志
        # 4. 更新数据库
        
        # 示例：调用回调函数
        if hasattr(self, 'signal_callback') and callable(self.signal_callback):
            try:
                await self.signal_callback(signal)
            except Exception as e:
                self.logger.error(f"信号回调异常: {e}")
    
    async def _start_websocket_streams(self, symbols: List[str], timeframes: List[str]):
        """启动WebSocket数据流"""
        # 这里是WebSocket连接的示例实现
        # 实际使用时需要根据具体交易所的API进行调整
        
        while self.running:
            try:
                # 模拟WebSocket数据接收
                await self._simulate_websocket_data(symbols, timeframes)
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"WebSocket数据流异常: {e}")
                await asyncio.sleep(5)
    
    async def _simulate_websocket_data(self, symbols: List[str], timeframes: List[str]):
        """模拟WebSocket数据（用于测试）"""
        # 这是一个模拟函数，实际使用时应该替换为真实的WebSocket数据接收
        import random
        
        for symbol in symbols:
            for timeframe in timeframes:
                # 生成模拟数据
                base_price = 50000 if 'BTC' in symbol else 3000
                price_change = random.uniform(-0.01, 0.01)
                
                current_price = base_price * (1 + price_change)
                
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    open=current_price * 0.999,
                    high=current_price * 1.001,
                    low=current_price * 0.998,
                    close=current_price,
                    volume=random.uniform(100, 1000),
                    timeframe=timeframe
                )
                
                self.data_buffer.add_data(symbol, timeframe, market_data)
    
    def _get_check_interval(self, timeframe: str) -> int:
        """获取检查间隔"""
        intervals = {
            '1m': 5,    # 5秒检查一次
            '5m': 10,   # 10秒检查一次
            '15m': 30,  # 30秒检查一次
            '30m': 60,  # 1分钟检查一次
            '1h': 120,  # 2分钟检查一次
            '4h': 300,  # 5分钟检查一次
            '1d': 600   # 10分钟检查一次
        }
        return intervals.get(timeframe, 60)
    
    def _calculate_confidence(self, df: pd.DataFrame, signal_type: int, signal_strength: float) -> float:
        """计算信号信心度"""
        confidence_factors = []
        
        # 信号强度
        confidence_factors.append(signal_strength)
        
        # 趋势一致性
        if len(df) >= 10:
            recent_trend = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
            if (signal_type == 1 and recent_trend > 0) or (signal_type == -1 and recent_trend < 0):
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.2)
        
        # 成交量确认
        if 'volume_ratio' in df.columns:
            volume_ratio = df['volume_ratio'].iloc[-1]
            if volume_ratio > 1.2:  # 成交量放大
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.3)
        
        # RSI确认
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if signal_type == 1 and 30 < rsi < 70:  # 买入信号，RSI不在极端区域
                confidence_factors.append(0.6)
            elif signal_type == -1 and 30 < rsi < 70:  # 卖出信号，RSI不在极端区域
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.4)
        
        return np.mean(confidence_factors)
    
    def _assess_risk_level(self, df: pd.DataFrame, signal_type: int, confidence: float) -> str:
        """评估风险等级"""
        risk_score = 0
        
        # 基于信心度
        if confidence > 0.7:
            risk_score += 1
        elif confidence < 0.4:
            risk_score -= 1
        
        # 基于波动率
        if 'atr' in df.columns and len(df) > 1:
            atr_ratio = df['atr'].iloc[-1] / df['close'].iloc[-1]
            if atr_ratio > 0.05:  # 高波动率
                risk_score -= 1
            elif atr_ratio < 0.02:  # 低波动率
                risk_score += 1
        
        # 基于市场状态
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if rsi > 80 or rsi < 20:  # 极端区域
                risk_score -= 1
        
        if risk_score >= 1:
            return 'low'
        elif risk_score == 0:
            return 'medium'
        else:
            return 'high'
    
    def _update_performance_stats(self, processing_time: float):
        """更新性能统计"""
        self.performance_stats['signals_generated'] += 1
        
        # 更新平均处理时间
        current_avg = self.performance_stats['avg_processing_time']
        count = self.performance_stats['signals_generated']
        
        new_avg = (current_avg * (count - 1) + processing_time) / count
        self.performance_stats['avg_processing_time'] = new_avg
        self.performance_stats['last_update'] = datetime.now()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def get_active_signals(self, symbol: str = None, timeframe: str = None) -> List[RealTimeSignal]:
        """获取活跃信号"""
        current_time = datetime.now()
        expiry_time = timedelta(seconds=self.signal_config['signal_expiry'])
        
        active_signals = [
            signal for signal in self.signal_history
            if current_time - signal.timestamp < expiry_time
        ]
        
        if symbol:
            active_signals = [s for s in active_signals if s.symbol == symbol]
        
        if timeframe:
            active_signals = [s for s in active_signals if s.timeframe == timeframe]
        
        return active_signals
    
    def set_signal_callback(self, callback: Callable):
        """设置信号回调函数"""
        self.signal_callback = callback
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        self.logger.info("停止实时信号监控")
    
    def add_strategy(self, name: str, strategy):
        """添加策略"""
        self.strategies[name] = strategy
        self.logger.info(f"添加策略: {name}")
    
    def remove_strategy(self, name: str):
        """移除策略"""
        if name in self.strategies:
            del self.strategies[name]
            self.logger.info(f"移除策略: {name}")
    
    def get_signal_summary(self) -> Dict[str, Any]:
        """获取信号摘要"""
        if not self.signal_history:
            return {'total_signals': 0}
        
        recent_signals = [
            s for s in self.signal_history
            if (datetime.now() - s.timestamp).total_seconds() < 3600  # 最近1小时
        ]
        
        buy_signals = [s for s in recent_signals if s.signal_type == 1]
        sell_signals = [s for s in recent_signals if s.signal_type == -1]
        
        return {
            'total_signals': len(self.signal_history),
            'recent_signals': len(recent_signals),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'avg_confidence': np.mean([s.confidence for s in recent_signals]) if recent_signals else 0,
            'avg_signal_strength': np.mean([s.signal_strength for s in recent_signals]) if recent_signals else 0,
            'symbols_active': len(set(s.symbol for s in recent_signals)),
            'last_signal_time': max(s.timestamp for s in self.signal_history) if self.signal_history else None
        }
