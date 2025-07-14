"""
策略基类 v2.0
统一策略接口，简化策略开发，支持策略组合和动态切换
从core/移动到framework/，专注于策略框架功能
"""

import asyncio
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import json

from .signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class StrategyState(Enum):
    """策略状态枚举"""
    INACTIVE = "inactive"    # 未激活
    ACTIVE = "active"        # 激活运行中
    PAUSED = "paused"        # 暂停
    ERROR = "error"          # 错误状态


class StrategyMetrics:
    """
    策略性能指标
    跟踪策略的各项性能数据
    """
    
    def __init__(self):
        # 信号统计
        self.total_signals = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.strong_signals = 0
        self.avg_strength = 0.0
        self.last_signal_time = None
        self.signal_frequency = 0.0  # 信号频率 (每小时)
        
        # 性能统计
        self.accuracy = 0.0      # 信号准确率
        self.precision = 0.0     # 精确率
        self.recall = 0.0        # 召回率
        self.sharpe_ratio = 0.0  # 夏普比率
        
        # 历史记录
        self.signal_history: List[Signal] = []
        self.performance_history: List[Dict] = []
        
        # 运行统计
        self.total_runtime = timedelta()
        self.error_count = 0
        self.last_error_time = None
    
    def add_signal(self, signal: Signal):
        """
        添加信号记录并更新统计
        
        Args:
            signal: 新产生的信号
        """
        self.total_signals += 1
        self.signal_history.append(signal)
        
        # 按信号类型统计
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            self.buy_signals += 1
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
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
    
    def add_error(self, error_msg: str):
        """记录错误"""
        self.error_count += 1
        self.last_error_time = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取指标摘要
        
        Returns:
            包含所有关键指标的字典
        """
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
            'recall': round(self.recall, 3),
            'sharpe_ratio': round(self.sharpe_ratio, 3),
            'error_count': self.error_count,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None
        }


class BaseStrategy(ABC):
    """
    策略基类 v2.0
    所有交易策略的基础类，定义统一的接口和通用功能
    """
    
    def __init__(self, name: str, config: Dict[str, Any], logger=None):
        """
        初始化策略
        
        Args:
            name: 策略名称，必须唯一
            config: 策略配置字典
            logger: 日志记录器（可选）
        """
        self.name = name
        self.config = config
        self.logger = logger
        
        # 策略状态管理
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
        
        # 风险控制参数
        self.risk_settings = config.get('risk_settings', {})
        self.min_signal_strength = self.risk_settings.get('min_signal_strength', 0.2)
        
        if self.logger:
            self.logger.info(f"🎯 策略初始化完成: {self.name}")
    
    @abstractmethod
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算技术指标
        子类必须实现此方法来计算策略所需的技术指标
        
        Args:
            data: OHLCV数据，包含columns: ['open', 'high', 'low', 'close', 'volume']
            symbol: 交易对符号
            
        Returns:
            添加了技术指标的DataFrame
        """
        pass
    
    @abstractmethod
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成交易信号
        子类必须实现此方法来生成具体的交易信号
        
        Args:
            data: 包含技术指标的OHLCV数据
            symbol: 交易对符号
            
        Returns:
            交易信号对象
        """
        pass
    
    async def process_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Signal]:
        """
        处理市场数据并生成信号
        这是策略的主要入口点
        
        Args:
            market_data: 市场数据字典 {symbol: DataFrame}
            
        Returns:
            信号字典 {symbol: Signal}
        """
        signals = {}
        
        for symbol, data in market_data.items():
            try:
                # 数据质量检查
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
                self.metrics.add_error(str(e))
                if self.logger:
                    self.logger.error(f"❌ 处理 {symbol} 数据失败: {e}")
                continue
        
        self.last_update_time = datetime.now()
        return signals
    
    def _validate_data(self, data: pd.DataFrame, symbol: str) -> bool:
        """
        验证数据质量
        
        Args:
            data: 市场数据
            symbol: 交易对符号
            
        Returns:
            数据是否有效
        """
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
        """
        验证信号有效性
        
        Args:
            signal: 生成的信号
            symbol: 交易对符号
            
        Returns:
            信号是否有效
        """
        if signal is None:
            return False
        
        # 检查信号强度
        if signal.strength < self.min_signal_strength:
            if self.logger:
                self.logger.debug(f"🔽 {symbol} 信号强度不足: {signal.strength}")
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
    
    # ==================== 状态管理方法 ====================
    
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
    
    # ==================== 参数管理方法 ====================
    
    def update_parameters(self, new_params: Dict[str, Any]):
        """
        更新策略参数
        
        Args:
            new_params: 新的参数字典
        """
        old_params = self.parameters.copy()
        self.parameters.update(new_params)
        
        if self.logger:
            self.logger.info(f"🔧 参数更新: {old_params} -> {self.parameters}")
    
    def get_parameter(self, key: str, default=None):
        """获取参数值"""
        return self.parameters.get(key, default)
    
    def set_parameter(self, key: str, value: Any):
        """设置单个参数"""
        self.parameters[key] = value
        if self.logger:
            self.logger.info(f"🔧 参数设置: {key} = {value}")
    
    # ==================== 缓存管理方法 ====================
    
    def get_cached_data(self, symbol: str, with_indicators: bool = False) -> Optional[pd.DataFrame]:
        """
        获取缓存的数据
        
        Args:
            symbol: 交易对符号
            with_indicators: 是否返回包含指标的数据
            
        Returns:
            缓存的数据或None
        """
        if with_indicators:
            return self.indicator_cache.get(symbol)
        else:
            return self.data_cache.get(symbol)
    
    def clear_cache(self, symbol: str = None):
        """
        清除缓存
        
        Args:
            symbol: 指定交易对，None表示清除所有
        """
        if symbol:
            self.data_cache.pop(symbol, None)
            self.indicator_cache.pop(symbol, None)
        else:
            self.data_cache.clear()
            self.indicator_cache.clear()
    
    # ==================== 状态查询方法 ====================
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取策略完整状态
        
        Returns:
            包含策略所有状态信息的字典
        """
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
            },
            'config': {
                'min_data_points': self.min_data_points,
                'signal_cooldown': self.signal_cooldown,
                'max_signals_per_hour': self.max_signals_per_hour,
                'min_signal_strength': self.min_signal_strength
            }
        }
    
    def export_signals(self, start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """
        导出信号历史
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            信号历史列表
        """
        signals = self.metrics.signal_history
        
        if start_time:
            signals = [s for s in signals if s.timestamp >= start_time]
        
        if end_time:
            signals = [s for s in signals if s.timestamp <= end_time]
        
        return [signal.to_dict() for signal in signals]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        
        Returns:
            详细的性能报告
        """
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
    
    # ==================== 工具方法 ====================
    
    def __str__(self):
        return f"{self.name}({self.state.value}, signals={self.metrics.total_signals})"
    
    def __repr__(self):
        return self.__str__()
