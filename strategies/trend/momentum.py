"""
动量策略
基于价格动量和变化率的趋势跟踪策略
从 legacy/strategy_examples.py 中分离
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from framework.strategy_base import BaseStrategy
from framework.signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class MomentumStrategy(BaseStrategy):
    """
    动量策略
    
    策略逻辑:
    1. 计算价格动量和变化率
    2. 监测动量加速度
    3. RSI过滤极端区域
    4. 动量强度决定信号强度
    """
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算动量指标
        
        Args:
            data: K线数据
            symbol: 交易对
            
        Returns:
            包含指标的DataFrame
        """
        # 计算基础指标
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 动量参数
        momentum_period = self.parameters.get('momentum_period', 10)
        roc_period = self.parameters.get('roc_period', 12)
        
        # 价格动量
        result['momentum'] = data['close'] / data['close'].shift(momentum_period) - 1
        
        # 变化率 (Rate of Change)
        result['roc'] = ((data['close'] - data['close'].shift(roc_period)) / data['close'].shift(roc_period)) * 100
        
        # 动量强度
        result['momentum_strength'] = abs(result['momentum'])
        
        # 动量方向
        result['momentum_direction'] = np.where(result['momentum'] > 0, 1, -1)
        
        # 动量加速度
        result['momentum_acceleration'] = result['momentum'].diff()
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成动量信号
        
        Args:
            data: 包含指标的K线数据
            symbol: 交易对
            
        Returns:
            交易信号
        """
        if len(data) < 3:
            return Signal(SignalType.HOLD, 0, data['close'].iloc[-1], "数据不足", {'symbol': symbol})
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 参数
        momentum_threshold = self.parameters.get('momentum_threshold', 0.02)
        rsi_filter = self.parameters.get('rsi_filter', True)
        rsi_min = self.parameters.get('rsi_min', 30)
        rsi_max = self.parameters.get('rsi_max', 70)
        
        # 获取指标值
        momentum = latest['momentum']
        roc = latest['roc']
        momentum_acceleration = latest['momentum_acceleration']
        rsi = latest['rsi']
        close_price = latest['close']
        
        # RSI过滤
        if rsi_filter and (rsi < rsi_min or rsi > rsi_max):
            return Signal(
                SignalType.HOLD,
                0.1,
                close_price,
                f"RSI过滤，RSI={rsi:.1f}",
                {'symbol': symbol}
            )
        
        # 正动量信号
        if momentum > momentum_threshold and momentum_acceleration > 0:
            strength = min(0.9, momentum * 5)  # 根据动量大小调整强度
            
            return Signal(
                SignalType.STRONG_BUY if strength > 0.7 else SignalType.BUY,
                strength,
                close_price,
                f"正动量加速，动量={momentum:.3f}, ROC={roc:.2f}",
                {
                    'symbol': symbol,
                    'momentum': momentum,
                    'roc': roc,
                    'acceleration': momentum_acceleration
                }
            )
        
        # 负动量信号
        elif momentum < -momentum_threshold and momentum_acceleration < 0:
            strength = min(0.9, abs(momentum) * 5)
            
            return Signal(
                SignalType.STRONG_SELL if strength > 0.7 else SignalType.SELL,
                strength,
                close_price,
                f"负动量加速，动量={momentum:.3f}, ROC={roc:.2f}",
                {
                    'symbol': symbol,
                    'momentum': momentum,
                    'roc': roc,
                    'acceleration': momentum_acceleration
                }
            )
        
        # 持有信号
        return Signal(
            SignalType.HOLD,
            0.1,
            close_price,
            f"动量不足，动量={momentum:.3f}",
            {'symbol': symbol}
        )