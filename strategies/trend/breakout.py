"""
突破策略
基于支撑阻力位突破的趋势跟踪策略
从 legacy/strategy_examples.py 中分离
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from framework.strategy_base import BaseStrategy
from framework.signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class BreakoutStrategy(BaseStrategy):
    """
    突破策略
    
    策略逻辑:
    1. 计算动态支撑阻力位
    2. 监测价格突破
    3. 成交量确认
    4. ATR调整止损
    """
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算突破指标
        
        Args:
            data: K线数据
            symbol: 交易对
            
        Returns:
            包含指标的DataFrame
        """
        # 计算基础指标
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 突破参数
        lookback_period = self.parameters.get('lookback_period', 20)
        
        # 计算支撑阻力位
        result['resistance'] = data['high'].rolling(window=lookback_period).max()
        result['support'] = data['low'].rolling(window=lookback_period).min()
        
        # 价格通道宽度
        result['channel_width'] = (result['resistance'] - result['support']) / result['support']
        
        # 突破信号
        result['breakout_up'] = data['close'] > result['resistance'].shift(1)
        result['breakout_down'] = data['close'] < result['support'].shift(1)
        
        # 成交量确认
        volume_ma = data['volume'].rolling(window=20).mean()
        result['volume_surge'] = data['volume'] > volume_ma * 1.5
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成突破信号
        
        Args:
            data: 包含指标的K线数据
            symbol: 交易对
            
        Returns:
            交易信号
        """
        if len(data) < 2:
            return Signal(SignalType.HOLD, 0, data['close'].iloc[-1], "数据不足", {'symbol': symbol})
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 参数
        min_channel_width = self.parameters.get('min_channel_width', 0.02)
        volume_confirmation = self.parameters.get('volume_confirmation', True)
        
        # 获取指标值
        close_price = latest['close']
        resistance = prev['resistance']  # 使用前一根K线的阻力位
        support = prev['support']        # 使用前一根K线的支撑位
        channel_width = latest['channel_width']
        volume_surge = latest['volume_surge']
        atr = latest['atr']
        
        # 检查通道宽度是否足够
        if channel_width < min_channel_width:
            return Signal(
                SignalType.HOLD,
                0.1,
                close_price,
                f"通道过窄，宽度={channel_width:.3f}",
                {'symbol': symbol}
            )
        
        # 向上突破
        if close_price > resistance:
            # 计算突破强度
            breakout_strength = (close_price - resistance) / atr
            strength = min(0.9, breakout_strength * 0.3)
            
            # 成交量确认
            if volume_confirmation and not volume_surge:
                strength *= 0.5  # 降低信号强度
            
            return Signal(
                SignalType.STRONG_BUY if strength > 0.7 else SignalType.BUY,
                strength,
                close_price,
                f"向上突破阻力位{resistance:.4f}，强度={breakout_strength:.2f}",
                {
                    'symbol': symbol,
                    'resistance': resistance,
                    'breakout_strength': breakout_strength,
                    'volume_surge': volume_surge
                }
            )
        
        # 向下突破
        elif close_price < support:
            # 计算突破强度
            breakout_strength = (support - close_price) / atr
            strength = min(0.9, breakout_strength * 0.3)
            
            # 成交量确认
            if volume_confirmation and not volume_surge:
                strength *= 0.5
            
            return Signal(
                SignalType.STRONG_SELL if strength > 0.7 else SignalType.SELL,
                strength,
                close_price,
                f"向下突破支撑位{support:.4f}，强度={breakout_strength:.2f}",
                {
                    'symbol': symbol,
                    'support': support,
                    'breakout_strength': breakout_strength,
                    'volume_surge': volume_surge
                }
            )
        
        # 持有信号
        return Signal(
            SignalType.HOLD,
            0.2,
            close_price,
            f"等待突破，价格在通道内",
            {'symbol': symbol}
        )