"""
策略实现示例
展示如何使用新的策略基类快速开发各种交易策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from .strategy_base import BaseStrategy, Signal, SignalType
from .indicators import TechnicalIndicators


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """计算均值回归指标"""
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
        """生成均值回归信号"""
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


class BreakoutStrategy(BaseStrategy):
    """突破策略"""
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """计算突破指标"""
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
        """生成突破信号"""
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
            0.1,
            close_price,
            f"价格在通道内，支撑{support:.4f}-阻力{resistance:.4f}",
            {'symbol': symbol}
        )


class MomentumStrategy(BaseStrategy):
    """动量策略"""
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """计算动量指标"""
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
        """生成动量信号"""
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


class ScalpingStrategy(BaseStrategy):
    """剥头皮策略（短线）"""
    
    async def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """计算短线指标"""
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
        """生成剥头皮信号"""
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


# 策略配置模板
STRATEGY_TEMPLATES = {
    'trend_following': {
        'parameters': {
            'fast_ema': 8,
            'slow_ema': 21,
            'rsi_threshold': 50
        },
        'timeframes': ['1h', '4h'],
        'min_data_points': 50,
        'signal_cooldown': 300,
        'max_signals_per_hour': 6
    },
    
    'mean_reversion': {
        'parameters': {
            'bb_period': 20,
            'bb_std': 2.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_threshold_low': 0.2,
            'bb_threshold_high': 0.8
        },
        'timeframes': ['1h'],
        'min_data_points': 30,
        'signal_cooldown': 600,
        'max_signals_per_hour': 4
    },
    
    'breakout': {
        'parameters': {
            'lookback_period': 20,
            'min_channel_width': 0.02,
            'volume_confirmation': True
        },
        'timeframes': ['4h', '1d'],
        'min_data_points': 40,
        'signal_cooldown': 1800,
        'max_signals_per_hour': 2
    },
    
    'momentum': {
        'parameters': {
            'momentum_period': 10,
            'roc_period': 12,
            'momentum_threshold': 0.02,
            'rsi_filter': True,
            'rsi_min': 30,
            'rsi_max': 70
        },
        'timeframes': ['1h'],
        'min_data_points': 25,
        'signal_cooldown': 300,
        'max_signals_per_hour': 8
    },
    
    'scalping': {
        'parameters': {
            'fast_ema': 5,
            'slow_ema': 13,
            'ema_diff_threshold': 0.001,
            'price_deviation_threshold': 0.002,
            'min_volatility': 0.005,
            'max_volatility': 0.02
        },
        'timeframes': ['5m', '15m'],
        'min_data_points': 20,
        'signal_cooldown': 60,
        'max_signals_per_hour': 20
    }
}
