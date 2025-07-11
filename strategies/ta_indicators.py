"""
Technical Analysis Indicators
Alternative to TA-Lib for basic indicators used in our strategies
"""

import numpy as np
import pandas as pd
from typing import Tuple, Union


def SMA(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
    """Simple Moving Average"""
    if isinstance(data, pd.Series):
        return data.rolling(window=period).mean().values
    else:
        return pd.Series(data).rolling(window=period).mean().values


def EMA(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
    """Exponential Moving Average"""
    if isinstance(data, pd.Series):
        return data.ewm(span=period).mean().values
    else:
        return pd.Series(data).ewm(span=period).mean().values


def RSI(data: Union[pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
    """Relative Strength Index"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values.values


def MACD(data: Union[pd.Series, np.ndarray], 
         fast_period: int = 12, 
         slow_period: int = 26, 
         signal_period: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD (Moving Average Convergence Divergence)"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    ema_fast = data.ewm(span=fast_period).mean()
    ema_slow = data.ewm(span=slow_period).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period).mean()
    histogram = macd_line - signal_line
    
    return macd_line.values, signal_line.values, histogram.values


def BOLLINGER_BANDS(data: Union[pd.Series, np.ndarray], 
                   period: int = 20, 
                   std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bollinger Bands"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper.values, middle.values, lower.values


def ATR(high: Union[pd.Series, np.ndarray], 
        low: Union[pd.Series, np.ndarray], 
        close: Union[pd.Series, np.ndarray], 
        period: int = 14) -> np.ndarray:
    """Average True Range"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    atr = pd.Series(true_range).rolling(window=period).mean()
    return atr.values


def STOCH(high: Union[pd.Series, np.ndarray], 
          low: Union[pd.Series, np.ndarray], 
          close: Union[pd.Series, np.ndarray], 
          k_period: int = 14, 
          d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """Stochastic Oscillator"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return k_percent.values, d_percent.values


def WILLIAMS_R(high: Union[pd.Series, np.ndarray], 
               low: Union[pd.Series, np.ndarray], 
               close: Union[pd.Series, np.ndarray], 
               period: int = 14) -> np.ndarray:
    """Williams %R"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
    return williams_r.values


def CCI(high: Union[pd.Series, np.ndarray], 
        low: Union[pd.Series, np.ndarray], 
        close: Union[pd.Series, np.ndarray], 
        period: int = 20) -> np.ndarray:
    """Commodity Channel Index"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=period).mean()
    mean_deviation = typical_price.rolling(window=period).apply(
        lambda x: np.mean(np.abs(x - np.mean(x)))
    )
    
    cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
    return cci.values


def MFI(high: Union[pd.Series, np.ndarray], 
        low: Union[pd.Series, np.ndarray], 
        close: Union[pd.Series, np.ndarray], 
        volume: Union[pd.Series, np.ndarray], 
        period: int = 14) -> np.ndarray:
    """Money Flow Index"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    money_ratio = positive_mf / negative_mf
    mfi = 100 - (100 / (1 + money_ratio))
    
    return mfi.values


def OBV(close: Union[pd.Series, np.ndarray], 
        volume: Union[pd.Series, np.ndarray]) -> np.ndarray:
    """On Balance Volume"""
    if isinstance(close, np.ndarray):
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    obv = volume.copy()
    obv[close < close.shift()] *= -1
    obv = obv.cumsum()
    
    return obv.values


def VWAP(high: Union[pd.Series, np.ndarray], 
         low: Union[pd.Series, np.ndarray], 
         close: Union[pd.Series, np.ndarray], 
         volume: Union[pd.Series, np.ndarray]) -> np.ndarray:
    """Volume Weighted Average Price"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
        volume = pd.Series(volume)
    
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap.values


def ADX(high: Union[pd.Series, np.ndarray], 
        low: Union[pd.Series, np.ndarray], 
        close: Union[pd.Series, np.ndarray], 
        period: int = 14) -> np.ndarray:
    """Average Directional Index"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    # Calculate True Range
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = np.abs(minus_dm)
    
    # Smooth the values
    atr = pd.Series(true_range).rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # Calculate ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx.values


def PLUS_DI(high: Union[pd.Series, np.ndarray], 
            low: Union[pd.Series, np.ndarray], 
            close: Union[pd.Series, np.ndarray], 
            period: int = 14) -> np.ndarray:
    """Plus Directional Indicator"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    # Calculate True Range
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    # Calculate Plus DM
    plus_dm = high.diff()
    plus_dm[plus_dm < 0] = 0
    
    # Smooth the values
    atr = pd.Series(true_range).rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    
    return plus_di.values


def MINUS_DI(high: Union[pd.Series, np.ndarray], 
             low: Union[pd.Series, np.ndarray], 
             close: Union[pd.Series, np.ndarray], 
             period: int = 14) -> np.ndarray:
    """Minus Directional Indicator"""
    if isinstance(high, np.ndarray):
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)
    
    # Calculate True Range
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    # Calculate Minus DM
    minus_dm = low.diff()
    minus_dm[minus_dm > 0] = 0
    minus_dm = np.abs(minus_dm)
    
    # Smooth the values
    atr = pd.Series(true_range).rolling(window=period).mean()
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    return minus_di.values


def MAX(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
    """Rolling Maximum"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    return data.rolling(window=period).max().values


def MIN(data: Union[pd.Series, np.ndarray], period: int) -> np.ndarray:
    """Rolling Minimum"""
    if isinstance(data, np.ndarray):
        data = pd.Series(data)
    
    return data.rolling(window=period).min().values


def MA(data: Union[pd.Series, np.ndarray], period: int, ma_type: str = 'SMA') -> np.ndarray:
    """Moving Average (SMA or EMA)"""
    if ma_type.upper() == 'EMA':
        return EMA(data, period)
    else:
        return SMA(data, period)


# Aliases for backward compatibility
sma = SMA
ema = EMA
rsi = RSI
macd = MACD
bollinger_bands = BOLLINGER_BANDS
atr = ATR
stoch = STOCH
williams_r = WILLIAMS_R
cci = CCI
mfi = MFI
obv = OBV
vwap = VWAP
adx = ADX
plus_di = PLUS_DI
minus_di = MINUS_DI
