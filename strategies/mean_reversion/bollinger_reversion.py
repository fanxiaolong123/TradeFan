"""
布林带均值回归策略
基于布林带和RSI的均值回归策略
从 legacy/strategy_examples.py 中分离
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from framework.strategy_base import BaseStrategy
from framework.signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    
    策略逻辑:
    1. 使用布林带识别超买超卖区域
    2. RSI确认极端位置
    3. 价格位置决定入场时机
    4. 趋势过滤避免逆势
    """
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算均值回归指标
        
        Args:
            data: K线数据
            symbol: 交易对
            
        Returns:
            包含指标的DataFrame
        """
        # 计算基础指标
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 布林带参数
        bb_period = self.parameters.get('bb_period', 20)
        bb_std = self.parameters.get('bb_std', 2.0)
        
        # 重新计算布林带（使用自定义参数）
        bb_upper, bb_middle, bb_lower = TechnicalIndicators.bollinger_bands(
            data['close'], bb_period, bb_std
        )
        
        result['bb_upper'] = bb_upper
        result['bb_middle'] = bb_middle
        result['bb_lower'] = bb_lower
        
        # 价格相对位置
        result['bb_position'] = (data['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # 均值回归信号
        result['mean_reversion_signal'] = np.where(
            result['bb_position'] < 0.2, 1,  # 超卖
            np.where(result['bb_position'] > 0.8, -1, 0)  # 超买
        )
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成均值回归信号
        
        Args:
            data: 包含指标的K线数据
            symbol: 交易对
            
        Returns:
            交易信号
        """
        if len(data) < 2:
            return Signal(SignalType.HOLD, 0, data['close'].iloc[-1], "数据不足", {'symbol': symbol})
        
        latest = data.iloc[-1]
        
        # 参数
        rsi_oversold = self.parameters.get('rsi_oversold', 30)
        rsi_overbought = self.parameters.get('rsi_overbought', 70)
        bb_threshold_low = self.parameters.get('bb_threshold_low', 0.2)
        bb_threshold_high = self.parameters.get('bb_threshold_high', 0.8)
        
        # 获取指标值
        rsi = latest['rsi']
        bb_position = latest['bb_position']
        close_price = latest['close']
        
        # 超卖信号（买入）
        if (bb_position < bb_threshold_low and rsi < rsi_oversold):
            strength = min(0.9, (rsi_oversold - rsi) / rsi_oversold + (bb_threshold_low - bb_position))
            return Signal(
                SignalType.STRONG_BUY if strength > 0.7 else SignalType.BUY,
                strength,
                close_price,
                f"均值回归超卖，RSI={rsi:.1f}, BB位置={bb_position:.2f}",
                {'symbol': symbol, 'rsi': rsi, 'bb_position': bb_position}
            )
        
        # 超买信号（卖出）
        elif (bb_position > bb_threshold_high and rsi > rsi_overbought):
            strength = min(0.9, (rsi - rsi_overbought) / (100 - rsi_overbought) + (bb_position - bb_threshold_high))
            return Signal(
                SignalType.STRONG_SELL if strength > 0.7 else SignalType.SELL,
                strength,
                close_price,
                f"均值回归超买，RSI={rsi:.1f}, BB位置={bb_position:.2f}",
                {'symbol': symbol, 'rsi': rsi, 'bb_position': bb_position}
            )
        
        # 持有信号
        return Signal(
            SignalType.HOLD,
            0.1,
            close_price,
            f"均值回归中性，RSI={rsi:.1f}",
            {'symbol': symbol}
        )