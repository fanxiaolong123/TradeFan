"""
高频剥头皮策略
基于快速EMA交叉和价格偏离的短线交易策略
从 legacy/strategy_examples.py 中分离
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from framework.strategy_base import BaseStrategy
from framework.signal import Signal, SignalType
from core.indicators import TechnicalIndicators


class ScalpingStrategy(BaseStrategy):
    """
    剥头皮策略（短线）
    
    策略逻辑:
    1. 使用快速EMA捕捉短期趋势
    2. 监测价格与EMA的偏离
    3. 波动率过滤确保市场活跃
    4. RSI避免极端区域
    """
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        计算短线指标
        
        Args:
            data: K线数据
            symbol: 交易对
            
        Returns:
            包含指标的DataFrame
        """
        # 计算基础指标
        result = TechnicalIndicators.calculate_all_indicators(data)
        
        # 短线参数
        fast_ema = self.parameters.get('fast_ema', 5)
        slow_ema = self.parameters.get('slow_ema', 13)
        
        # 快速EMA
        result[f'ema_{fast_ema}'] = TechnicalIndicators.ema(data['close'], fast_ema)
        result[f'ema_{slow_ema}'] = TechnicalIndicators.ema(data['close'], slow_ema)
        
        # EMA差值
        result['ema_diff'] = result[f'ema_{fast_ema}'] - result[f'ema_{slow_ema}']
        result['ema_diff_pct'] = result['ema_diff'] / result[f'ema_{slow_ema}']
        
        # 价格与EMA的偏离
        result['price_ema_diff'] = (data['close'] - result[f'ema_{fast_ema}']) / result[f'ema_{fast_ema}']
        
        # 短期波动率
        result['short_volatility'] = data['close'].pct_change().rolling(window=10).std()
        
        return result
    
    async def generate_signal(self, data: pd.DataFrame, symbol: str) -> Signal:
        """
        生成剥头皮信号
        
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
        ema_diff_threshold = self.parameters.get('ema_diff_threshold', 0.001)
        price_deviation_threshold = self.parameters.get('price_deviation_threshold', 0.002)
        min_volatility = self.parameters.get('min_volatility', 0.005)
        max_volatility = self.parameters.get('max_volatility', 0.02)
        
        # 获取指标值
        fast_ema = self.parameters.get('fast_ema', 5)
        slow_ema = self.parameters.get('slow_ema', 13)
        
        ema_diff_pct = latest['ema_diff_pct']
        price_ema_diff = latest['price_ema_diff']
        volatility = latest['short_volatility']
        rsi = latest['rsi']
        close_price = latest['close']
        
        # 波动率过滤
        if volatility < min_volatility or volatility > max_volatility:
            return Signal(
                SignalType.HOLD,
                0.1,
                close_price,
                f"波动率不适合，波动率={volatility:.4f}",
                {'symbol': symbol}
            )
        
        # 快速上涨信号
        if (ema_diff_pct > ema_diff_threshold and 
            price_ema_diff > -price_deviation_threshold and
            rsi < 80):
            
            strength = min(0.8, ema_diff_pct * 100)  # 短线策略强度适中
            
            return Signal(
                SignalType.BUY,  # 剥头皮通常不用强信号
                strength,
                close_price,
                f"短线上涨，EMA差值={ema_diff_pct:.4f}",
                {
                    'symbol': symbol,
                    'ema_diff_pct': ema_diff_pct,
                    'price_deviation': price_ema_diff,
                    'volatility': volatility
                }
            )
        
        # 快速下跌信号
        elif (ema_diff_pct < -ema_diff_threshold and 
              price_ema_diff < price_deviation_threshold and
              rsi > 20):
            
            strength = min(0.8, abs(ema_diff_pct) * 100)
            
            return Signal(
                SignalType.SELL,
                strength,
                close_price,
                f"短线下跌，EMA差值={ema_diff_pct:.4f}",
                {
                    'symbol': symbol,
                    'ema_diff_pct': ema_diff_pct,
                    'price_deviation': price_ema_diff,
                    'volatility': volatility
                }
            )
        
        # 持有信号
        return Signal(
            SignalType.HOLD,
            0.1,
            close_price,
            f"短线中性，EMA差值={ema_diff_pct:.4f}",
            {'symbol': symbol}
        )