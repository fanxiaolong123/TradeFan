"""
趋势跟踪策略
基于EMA交叉和RSI过滤的经典趋势跟踪策略
从core/strategy_examples.py移动到strategies/trend/
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from framework.strategy_base import BaseStrategy
from framework.signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略
    
    策略逻辑:
    1. 使用快慢EMA交叉判断趋势方向
    2. RSI过滤避免极端区域入场
    3. 趋势强度确定信号强度
    
    参数:
    - fast_ema: 快速EMA周期，默认8
    - slow_ema: 慢速EMA周期，默认21
    - rsi_threshold: RSI中性阈值，默认50
    - rsi_overbought: RSI超买阈值，默认80
    - rsi_oversold: RSI超卖阈值，默认20
    """
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算趋势跟踪所需的技术指标
        
        Args:
            data: OHLCV数据
            symbol: 交易对符号
            
        Returns:
            包含技术指标的数据
        """
        # 使用统一的技术指标计算器
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 获取策略参数
        fast_ema = self.get_parameter('fast_ema', 8)
        slow_ema = self.get_parameter('slow_ema', 21)
        
        # 计算自定义EMA（如果参数与默认不同）
        if fast_ema != 8:
            result[f'ema_{fast_ema}'] = TechnicalIndicators.ema(data['close'], fast_ema)
        if slow_ema != 21:
            result[f'ema_{slow_ema}'] = TechnicalIndicators.ema(data['close'], slow_ema)
        
        # 计算趋势强度
        result['trend_strength'] = abs(result[f'ema_{fast_ema}'] - result[f'ema_{slow_ema}']) / result[f'ema_{slow_ema}']
        
        # 计算EMA斜率（趋势方向确认）
        result['ema_fast_slope'] = result[f'ema_{fast_ema}'].diff() / result[f'ema_{fast_ema}']
        result['ema_slow_slope'] = result[f'ema_{slow_ema}'].diff() / result[f'ema_{slow_ema}']
        
        # 价格相对EMA位置
        result['price_above_fast_ema'] = data['close'] > result[f'ema_{fast_ema}']
        result['price_above_slow_ema'] = data['close'] > result[f'ema_{slow_ema}']
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成趋势跟踪信号
        
        Args:
            data: 包含技术指标的数据
            symbol: 交易对符号
            
        Returns:
            交易信号
        """
        if len(data) < 2:
            return Signal(
                SignalType.HOLD, 0, data['close'].iloc[-1], 
                "数据不足", {'symbol': symbol}
            )
        
        # 获取最新和前一个数据点
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 获取策略参数
        fast_ema = self.get_parameter('fast_ema', 8)
        slow_ema = self.get_parameter('slow_ema', 21)
        rsi_threshold = self.get_parameter('rsi_threshold', 50)
        rsi_overbought = self.get_parameter('rsi_overbought', 80)
        rsi_oversold = self.get_parameter('rsi_oversold', 20)
        
        # 获取指标值
        ema_fast_current = latest[f'ema_{fast_ema}']
        ema_slow_current = latest[f'ema_{slow_ema}']
        ema_fast_prev = prev[f'ema_{fast_ema}']
        ema_slow_prev = prev[f'ema_{slow_ema}']
        
        rsi = latest['rsi']
        trend_strength = latest['trend_strength']
        close_price = latest['close']
        
        # 检测EMA交叉
        golden_cross = (ema_fast_current > ema_slow_current and 
                       ema_fast_prev <= ema_slow_prev)  # 金叉
        death_cross = (ema_fast_current < ema_slow_current and 
                      ema_fast_prev >= ema_slow_prev)   # 死叉
        
        # 趋势确认条件
        uptrend_confirmed = (ema_fast_current > ema_slow_current and
                           latest['ema_fast_slope'] > 0 and
                           latest['ema_slow_slope'] > 0)
        
        downtrend_confirmed = (ema_fast_current < ema_slow_current and
                             latest['ema_fast_slope'] < 0 and
                             latest['ema_slow_slope'] < 0)
        
        # 多头信号条件
        if golden_cross and rsi > rsi_threshold and rsi < rsi_overbought:
            # 计算信号强度
            strength = min(0.9, trend_strength * 5 + 0.3)  # 基础强度0.3，趋势强度加成
            
            # 额外确认因素
            if uptrend_confirmed:
                strength += 0.1
            if latest['price_above_fast_ema'] and latest['price_above_slow_ema']:
                strength += 0.1
            
            strength = min(0.95, strength)  # 限制最大强度
            
            signal_type = SignalType.STRONG_BUY if strength > 0.7 else SignalType.BUY
            
            return Signal(
                signal_type, strength, close_price,
                f"趋势金叉确认，RSI={rsi:.1f}，趋势强度={trend_strength:.3f}",
                {
                    'symbol': symbol,
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'rsi': rsi,
                    'trend_strength': trend_strength,
                    'golden_cross': True,
                    'uptrend_confirmed': uptrend_confirmed
                }
            )
        
        # 空头信号条件
        elif death_cross and rsi < rsi_threshold and rsi > rsi_oversold:
            # 计算信号强度
            strength = min(0.9, trend_strength * 5 + 0.3)
            
            # 额外确认因素
            if downtrend_confirmed:
                strength += 0.1
            if not latest['price_above_fast_ema'] and not latest['price_above_slow_ema']:
                strength += 0.1
            
            strength = min(0.95, strength)
            
            signal_type = SignalType.STRONG_SELL if strength > 0.7 else SignalType.SELL
            
            return Signal(
                signal_type, strength, close_price,
                f"趋势死叉确认，RSI={rsi:.1f}，趋势强度={trend_strength:.3f}",
                {
                    'symbol': symbol,
                    'ema_fast': ema_fast_current,
                    'ema_slow': ema_slow_current,
                    'rsi': rsi,
                    'trend_strength': trend_strength,
                    'death_cross': True,
                    'downtrend_confirmed': downtrend_confirmed
                }
            )
        
        # 趋势持续信号（较弱）
        elif uptrend_confirmed and rsi > 40 and rsi < 75:
            return Signal(
                SignalType.HOLD, 0.2, close_price,
                f"上升趋势持续，RSI={rsi:.1f}",
                {'symbol': symbol, 'trend': 'up', 'strength': 'weak'}
            )
        
        elif downtrend_confirmed and rsi < 60 and rsi > 25:
            return Signal(
                SignalType.HOLD, 0.2, close_price,
                f"下降趋势持续，RSI={rsi:.1f}",
                {'symbol': symbol, 'trend': 'down', 'strength': 'weak'}
            )
        
        # 无明确信号
        else:
            reason = "无明确趋势信号"
            if rsi >= rsi_overbought:
                reason = f"RSI超买区域({rsi:.1f})"
            elif rsi <= rsi_oversold:
                reason = f"RSI超卖区域({rsi:.1f})"
            elif trend_strength < 0.01:
                reason = f"趋势强度不足({trend_strength:.3f})"
            
            return Signal(
                SignalType.HOLD, 0.1, close_price, reason,
                {'symbol': symbol, 'rsi': rsi, 'trend_strength': trend_strength}
            )
