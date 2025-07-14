"""
策略基类 v2.0
统一策略接口，简化策略开发，支持策略组合和动态切换
"""

import asyncio
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import json

from .indicators import TechnicalIndicators
from .logger import LoggerManager


class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1
    SELL = -1
    HOLD = 0
    STRONG_BUY = 2
    STRONG_SELL = -2


class StrategyState(Enum):
    """策略状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class Signal:
    """交易信号类"""
    
    def __init__(self, signal_type: SignalType, strength: float, 
                 price: float, reason: str, metadata: Dict[str, Any] = None):
        """
        初始化交易信号
        
        Args:
            signal_type: 信号类型
            strength: 信号强度 (0-1)
            price: 触发价格
            reason: 信号原因
            metadata: 额外元数据
        """
        self.signal_type = signal_type
        self.strength = max(0, min(1, strength))  # 限制在0-1之间
        self.price = price
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.symbol = self.metadata.get('symbol', '')
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'signal': self.signal_type.value,
            'strength': self.strength,
            'price': self.price,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'metadata': self.metadata
        }
    
    def is_entry_signal(self) -> bool:
        """是否为入场信号"""
        return self.signal_type in [SignalType.BUY, SignalType.SELL, 
                                   SignalType.STRONG_BUY, SignalType.STRONG_SELL]
    
    def is_strong_signal(self) -> bool:
        """是否为强信号"""
        return self.signal_type in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]
    
    def __str__(self):
        return f"Signal({self.signal_type.name}, {self.strength:.2f}, {self.reason})"


class StrategyMetrics:
    """策略性能指标"""
    
    def __init__(self):
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.strong_signals = 0
        self.avg_strength = 0.0
        self.last_signal_time = None
        self.signal_frequency = 0.0  # 信号频率 (每小时)
        
        # 性能统计
        self.accuracy = 0.0  # 信号准确率
        self.precision = 0.0  # 精确率
        self.recall = 0.0    # 召回率
        
        # 历史记录
        self.signal_history: List[Signal] = []
        self.performance_history: List[Dict] = []
    
    def add_signal(self, signal: Signal):
        """添加信号记录"""
        self.total_signals += 1
        self.signal_history.append(signal)
        
        if signal.signal_type == SignalType.BUY:
            self.buy_signals += 1
        elif signal.signal_type == SignalType.SELL:
            self.sell_signals += 1
        
        if signal.is_strong_signal():
            self.strong_signals += 1
        
        # 更新平均强度
        total_strength = sum(s.strength for s in self.signal_history)
        self.avg_strength = total_strength / len(self.signal_history)
        
        self.last_signal_time = signal.timestamp
        
        # 计算信号频率 (最近24小时)
        recent_signals = [s for s in self.signal_history 
                         if (datetime.now() - s.timestamp).total_seconds() < 86400]
        self.signal_frequency = len(recent_signals) / 24.0
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            'total_signals': self.total_signals,
            'buy_signals': self.buy_signals,
            'sell_signals': self.sell_signals,
            'strong_signals': self.strong_signals,
            'avg_strength': round(self.avg_strength, 3),
            'signal_frequency': round(self.signal_frequency, 2),
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'accuracy': round(self.accuracy, 3),
            'precision': round(self.precision, 3),
            'recall': round(self.recall, 3)
        }


class BaseStrategy(ABC):
    """策略基类 v2.0"""
    
    def __init__(self, name: str, config: Dict[str, Any], 
                 logger_manager: LoggerManager = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            config: 策略配置
            logger_manager: 日志管理器
        """
        self.name = name
        self.config = config
        self.logger_manager = logger_manager
        self.logger = logger_manager.get_strategy_logger(name) if logger_manager else None
        
        # 策略状态
        self.state = StrategyState.INACTIVE
        self.created_time = datetime.now()
        self.last_update_time = None
        
        # 策略参数
        self.parameters = config.get('parameters', {})
        self.timeframes = config.get('timeframes', ['1h'])
        self.symbols = config.get('symbols', [])
        
        # 性能指标
        self.metrics = StrategyMetrics()
        
        # 数据缓存
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.indicator_cache: Dict[str, pd.DataFrame] = {}
        
        # 策略特定配置
        self.min_data_points = config.get('min_data_points', 50)
        self.signal_cooldown = config.get('signal_cooldown', 300)  # 秒
        self.max_signals_per_hour = config.get('max_signals_per_hour', 10)
        
        if self.logger:
            self.logger.info(f"🎯 策略初始化: {self.name}")
    
    @abstractmethod
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: OHLCV数据
            symbol: 交易对
            
        Returns:
            包含技术指标的数据
        """
        pass
    
    @abstractmethod
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成交易信号
        
        Args:
            data: 包含技术指标的数据
            symbol: 交易对
            
        Returns:
            交易信号
        """
        pass
    
    async def process_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Signal]:
        """
        处理市场数据并生成信号
        
        Args:
            market_data: 市场数据字典 {symbol: DataFrame}
            
        Returns:
            信号字典 {symbol: Signal}
        """
        signals = {}
        
        for symbol, data in market_data.items():
            try:
                # 检查数据质量
                if not self._validate_data(data, symbol):
                    continue
                
                # 计算技术指标
                data_with_indicators = await self.calculate_indicators(data, symbol)
                
                # 缓存数据
                self.data_cache[symbol] = data
                self.indicator_cache[symbol] = data_with_indicators
                
                # 生成信号
                signal = await self.generate_signal(data_with_indicators, symbol)
                
                # 验证信号
                if self._validate_signal(signal, symbol):
                    signals[symbol] = signal
                    self.metrics.add_signal(signal)
                    
                    if self.logger:
                        self.logger.info(f"📊 {symbol} 信号: {signal}")
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ 处理 {symbol} 数据失败: {e}")
                continue
        
        self.last_update_time = datetime.now()
        return signals
    
    def _validate_data(self, data: pd.DataFrame, symbol: str) -> bool:
        """验证数据质量"""
        if data is None or len(data) < self.min_data_points:
            if self.logger:
                self.logger.warning(f"⚠️ {symbol} 数据不足: {len(data) if data is not None else 0}")
            return False
        
        # 检查必需列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            if self.logger:
                self.logger.error(f"❌ {symbol} 缺少列: {missing_columns}")
            return False
        
        # 检查数据完整性
        if data[required_columns].isnull().any().any():
            if self.logger:
                self.logger.warning(f"⚠️ {symbol} 数据包含空值")
            return False
        
        return True
    
    def _validate_signal(self, signal: Signal, symbol: str) -> bool:
        """验证信号有效性"""
        if signal is None:
            return False
        
        # 检查信号冷却时间
        if self.signal_cooldown > 0:
            recent_signals = [s for s in self.metrics.signal_history 
                            if s.symbol == symbol and 
                            (datetime.now() - s.timestamp).total_seconds() < self.signal_cooldown]
            
            if recent_signals:
                if self.logger:
                    self.logger.debug(f"🔄 {symbol} 信号冷却中")
                return False
        
        # 检查信号频率限制
        if self.max_signals_per_hour > 0:
            recent_hour_signals = [s for s in self.metrics.signal_history 
                                 if (datetime.now() - s.timestamp).total_seconds() < 3600]
            
            if len(recent_hour_signals) >= self.max_signals_per_hour:
                if self.logger:
                    self.logger.warning(f"⚠️ 信号频率过高，跳过 {symbol}")
                return False
        
        return True
    
    def get_cached_data(self, symbol: str, with_indicators: bool = False) -> Optional[pd.DataFrame]:
        """获取缓存的数据"""
        if with_indicators:
            return self.indicator_cache.get(symbol)
        else:
            return self.data_cache.get(symbol)
    
    def clear_cache(self, symbol: str = None):
        """清除缓存"""
        if symbol:
            self.data_cache.pop(symbol, None)
            self.indicator_cache.pop(symbol, None)
        else:
            self.data_cache.clear()
            self.indicator_cache.clear()
    
    def activate(self):
        """激活策略"""
        self.state = StrategyState.ACTIVE
        if self.logger:
            self.logger.info(f"✅ 策略激活: {self.name}")
    
    def deactivate(self):
        """停用策略"""
        self.state = StrategyState.INACTIVE
        if self.logger:
            self.logger.info(f"⏹️ 策略停用: {self.name}")
    
    def pause(self):
        """暂停策略"""
        self.state = StrategyState.PAUSED
        if self.logger:
            self.logger.info(f"⏸️ 策略暂停: {self.name}")
    
    def resume(self):
        """恢复策略"""
        self.state = StrategyState.ACTIVE
        if self.logger:
            self.logger.info(f"▶️ 策略恢复: {self.name}")
    
    def update_parameters(self, new_params: Dict[str, Any]):
        """更新策略参数"""
        old_params = self.parameters.copy()
        self.parameters.update(new_params)
        
        if self.logger:
            self.logger.info(f"🔧 参数更新: {old_params} -> {self.parameters}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            'name': self.name,
            'state': self.state.value,
            'created_time': self.created_time.isoformat(),
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'parameters': self.parameters.copy(),
            'timeframes': self.timeframes,
            'symbols': self.symbols,
            'metrics': self.metrics.get_summary(),
            'cache_size': {
                'data': len(self.data_cache),
                'indicators': len(self.indicator_cache)
            }
        }
    
    def export_signals(self, start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """导出信号历史"""
        signals = self.metrics.signal_history
        
        if start_time:
            signals = [s for s in signals if s.timestamp >= start_time]
        
        if end_time:
            signals = [s for s in signals if s.timestamp <= end_time]
        
        return [signal.to_dict() for signal in signals]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        metrics = self.metrics.get_summary()
        
        # 计算运行时间
        runtime = datetime.now() - self.created_time
        
        # 计算信号分布
        signal_distribution = {}
        for signal in self.metrics.signal_history:
            signal_type = signal.signal_type.name
            signal_distribution[signal_type] = signal_distribution.get(signal_type, 0) + 1
        
        return {
            'strategy_name': self.name,
            'runtime_hours': round(runtime.total_seconds() / 3600, 2),
            'current_state': self.state.value,
            'metrics': metrics,
            'signal_distribution': signal_distribution,
            'parameters': self.parameters,
            'cache_status': {
                'symbols_cached': list(self.data_cache.keys()),
                'cache_size': len(self.data_cache)
            }
        }
    
    def __str__(self):
        return f"{self.name}({self.state.value}, signals={self.metrics.total_signals})"
    
    def __repr__(self):
        return self.__str__()


class StrategyTemplate:
    """策略模板，用于快速创建常见策略"""
    
    @staticmethod
    def create_trend_following_strategy(name: str, config: Dict[str, Any]) -> 'TrendFollowingStrategy':
        """创建趋势跟踪策略"""
        return TrendFollowingStrategy(name, config)
    
    @staticmethod
    def create_mean_reversion_strategy(name: str, config: Dict[str, Any]) -> 'MeanReversionStrategy':
        """创建均值回归策略"""
        return MeanReversionStrategy(name, config)
    
    @staticmethod
    def create_breakout_strategy(name: str, config: Dict[str, Any]) -> 'BreakoutStrategy':
        """创建突破策略"""
        return BreakoutStrategy(name, config)


# 示例策略实现
class TrendFollowingStrategy(BaseStrategy):
    """趋势跟踪策略示例"""
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """计算趋势指标"""
        # 使用统一的技术指标计算器
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 添加自定义指标
        fast_ema = self.parameters.get('fast_ema', 8)
        slow_ema = self.parameters.get('slow_ema', 21)
        
        result[f'ema_{fast_ema}'] = TechnicalIndicators.ema(data['close'], fast_ema)
        result[f'ema_{slow_ema}'] = TechnicalIndicators.ema(data['close'], slow_ema)
        
        # 趋势强度
        result['trend_strength'] = abs(result[f'ema_{fast_ema}'] - result[f'ema_{slow_ema}']) / result[f'ema_{slow_ema}']
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """生成趋势信号"""
        if len(data) < 2:
            return Signal(SignalType.HOLD, 0, data['close'].iloc[-1], "数据不足", {'symbol': symbol})
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        fast_ema = self.parameters.get('fast_ema', 8)
        slow_ema = self.parameters.get('slow_ema', 21)
        rsi_threshold = self.parameters.get('rsi_threshold', 50)
        
        # 趋势信号逻辑
        ema_fast = latest[f'ema_{fast_ema}']
        ema_slow = latest[f'ema_{slow_ema}']
        rsi = latest['rsi']
        trend_strength = latest['trend_strength']
        
        # 多头信号
        if (ema_fast > ema_slow and 
            prev[f'ema_{fast_ema}'] <= prev[f'ema_{slow_ema}'] and  # 金叉
            rsi > rsi_threshold and rsi < 80):
            
            strength = min(0.9, trend_strength * 5)  # 根据趋势强度调整信号强度
            return Signal(
                SignalType.STRONG_BUY if strength > 0.7 else SignalType.BUY,
                strength,
                latest['close'],
                f"趋势金叉，RSI={rsi:.1f}",
                {'symbol': symbol, 'ema_fast': ema_fast, 'ema_slow': ema_slow}
            )
        
        # 空头信号
        elif (ema_fast < ema_slow and 
              prev[f'ema_{fast_ema}'] >= prev[f'ema_{slow_ema}'] and  # 死叉
              rsi < rsi_threshold and rsi > 20):
            
            strength = min(0.9, trend_strength * 5)
            return Signal(
                SignalType.STRONG_SELL if strength > 0.7 else SignalType.SELL,
                strength,
                latest['close'],
                f"趋势死叉，RSI={rsi:.1f}",
                {'symbol': symbol, 'ema_fast': ema_fast, 'ema_slow': ema_slow}
            )
        
        # 持有信号
        return Signal(
            SignalType.HOLD,
            0.1,
            latest['close'],
            f"趋势持续，无交叉信号",
            {'symbol': symbol}
        )
