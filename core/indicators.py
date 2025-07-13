"""
统一技术指标计算器
消除重复代码，提供标准化的技术指标计算
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class TechnicalIndicators:
    """统一技术指标计算器"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int, adjust: bool = False) -> pd.Series:
        """计算指数移动平均线"""
        return data.ewm(span=period, adjust=adjust).mean()
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """计算简单移动平均线"""
        return data.rolling(window=period, min_periods=1).mean()
    
    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """计算布林带"""
        middle = data.rolling(window=period, min_periods=1).mean()
        std = data.rolling(window=period, min_periods=1).std()
        
        return {
            'bb_upper': middle + (std * std_dev),
            'bb_middle': middle,
            'bb_lower': middle - (std * std_dev),
            'bb_width': (std * std_dev * 2) / middle
        }
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """计算相对强弱指数"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        ema_fast = TechnicalIndicators.calculate_ema(data, fast)
        ema_slow = TechnicalIndicators.calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': histogram
        }
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """计算平均真实波幅"""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        return true_range.rolling(window=period, min_periods=1).mean()
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """计算随机指标"""
        lowest_low = low.rolling(window=k_period, min_periods=1).min()
        highest_high = high.rolling(window=k_period, min_periods=1).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period, min_periods=1).mean()
        
        return {
            'stoch_k': k_percent,
            'stoch_d': d_percent
        }
    
    @staticmethod
    def calculate_volume_indicators(volume: pd.Series, period: int = 20) -> Dict[str, pd.Series]:
        """计算成交量指标"""
        volume_ma = volume.rolling(window=period, min_periods=1).mean()
        volume_ratio = volume / volume_ma
        
        return {
            'volume_ma': volume_ma,
            'volume_ratio': volume_ratio,
            'volume_trend': volume_ma / volume_ma.shift(5)
        }
    
    @staticmethod
    def calculate_momentum_indicators(close: pd.Series) -> Dict[str, pd.Series]:
        """计算动量指标"""
        return {
            'momentum_5': close / close.shift(5) - 1,
            'momentum_10': close / close.shift(10) - 1,
            'momentum_20': close / close.shift(20) - 1,
            'price_change': close.pct_change(),
            'price_change_5': close.pct_change(5)
        }
    
    @staticmethod
    def calculate_trend_indicators(close: pd.Series) -> Dict[str, pd.Series]:
        """计算趋势指标"""
        ema_8 = TechnicalIndicators.calculate_ema(close, 8)
        ema_21 = TechnicalIndicators.calculate_ema(close, 21)
        ema_55 = TechnicalIndicators.calculate_ema(close, 55)
        
        return {
            'ema_8': ema_8,
            'ema_21': ema_21,
            'ema_55': ema_55,
            'trend_strength': abs(ema_8 - ema_21) / ema_21,
            'trend_direction': np.where(ema_8 > ema_21, 1, -1)
        }
    
    @staticmethod
    def calculate_all_indicators(data: pd.DataFrame, 
                               config: Optional[Dict] = None) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            data: OHLCV数据
            config: 指标参数配置
        
        Returns:
            包含所有指标的DataFrame
        """
        if config is None:
            config = {
                'ema_periods': [8, 21, 55],
                'bb_period': 20,
                'bb_std': 2.0,
                'rsi_period': 14,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'atr_period': 14,
                'volume_period': 20
            }
        
        result = data.copy()
        
        try:
            # 趋势指标
            for period in config['ema_periods']:
                result[f'ema_{period}'] = TechnicalIndicators.calculate_ema(data['close'], period)
            
            # 布林带
            bb_data = TechnicalIndicators.calculate_bollinger_bands(
                data['close'], config['bb_period'], config['bb_std']
            )
            for key, value in bb_data.items():
                result[key] = value
            
            # RSI
            result['rsi'] = TechnicalIndicators.calculate_rsi(data['close'], config['rsi_period'])
            
            # MACD
            macd_data = TechnicalIndicators.calculate_macd(
                data['close'], config['macd_fast'], config['macd_slow'], config['macd_signal']
            )
            for key, value in macd_data.items():
                result[key] = value
            
            # ATR
            result['atr'] = TechnicalIndicators.calculate_atr(
                data['high'], data['low'], data['close'], config['atr_period']
            )
            
            # 成交量指标
            if 'volume' in data.columns:
                volume_data = TechnicalIndicators.calculate_volume_indicators(
                    data['volume'], config['volume_period']
                )
                for key, value in volume_data.items():
                    result[key] = value
            
            # 动量指标
            momentum_data = TechnicalIndicators.calculate_momentum_indicators(data['close'])
            for key, value in momentum_data.items():
                result[key] = value
            
            # 趋势指标
            trend_data = TechnicalIndicators.calculate_trend_indicators(data['close'])
            for key, value in trend_data.items():
                result[key] = value
            
        except Exception as e:
            print(f"⚠️  指标计算警告: {str(e)}")
        
        return result
    
    @staticmethod
    def get_signal_strength(data: pd.DataFrame, 
                          signal_config: Optional[Dict] = None) -> pd.Series:
        """
        计算综合信号强度
        
        Args:
            data: 包含技术指标的数据
            signal_config: 信号配置参数
        
        Returns:
            信号强度序列 (-1到1之间)
        """
        if signal_config is None:
            signal_config = {
                'trend_weight': 0.4,
                'momentum_weight': 0.3,
                'volume_weight': 0.2,
                'volatility_weight': 0.1
            }
        
        try:
            # 趋势信号
            trend_signal = 0
            if all(col in data.columns for col in ['ema_8', 'ema_21', 'ema_55']):
                trend_conditions = [
                    data['ema_8'] > data['ema_21'],
                    data['ema_21'] > data['ema_55'],
                    data['close'] > data['bb_middle']
                ]
                trend_signal = (sum(trend_conditions) / len(trend_conditions) - 0.5) * 2
            
            # 动量信号
            momentum_signal = 0
            if 'rsi' in data.columns and 'macd' in data.columns:
                rsi_signal = np.where(
                    (data['rsi'] > 30) & (data['rsi'] < 70), 
                    (data['rsi'] - 50) / 50, 0
                )
                macd_signal = np.where(
                    data['macd'] > data['macd_signal'], 0.5, -0.5
                )
                momentum_signal = (rsi_signal + macd_signal) / 2
            
            # 成交量信号
            volume_signal = 0
            if 'volume_ratio' in data.columns:
                volume_signal = np.where(data['volume_ratio'] > 1.5, 0.5, 0)
            
            # 波动率信号
            volatility_signal = 0
            if 'bb_width' in data.columns:
                volatility_signal = np.where(data['bb_width'] > data['bb_width'].rolling(20).mean(), 0.3, -0.3)
            
            # 综合信号
            total_signal = (
                trend_signal * signal_config['trend_weight'] +
                momentum_signal * signal_config['momentum_weight'] +
                volume_signal * signal_config['volume_weight'] +
                volatility_signal * signal_config['volatility_weight']
            )
            
            return pd.Series(total_signal, index=data.index)
            
        except Exception as e:
            print(f"⚠️  信号计算警告: {str(e)}")
            return pd.Series(0, index=data.index)


# 便捷函数
def add_all_indicators(data: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
    """便捷函数：为数据添加所有技术指标"""
    return TechnicalIndicators.calculate_all_indicators(data, config)

def get_trading_signal(data: pd.DataFrame, threshold: float = 0.3) -> pd.Series:
    """便捷函数：获取交易信号"""
    signal_strength = TechnicalIndicators.get_signal_strength(data)
    
    return pd.Series(
        np.where(signal_strength > threshold, 1,
                np.where(signal_strength < -threshold, -1, 0)),
        index=data.index
    )


# 测试函数
def test_indicators():
    """测试技术指标计算器"""
    print("🧪 测试技术指标计算器...")
    
    # 生成测试数据
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    close_prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
    high_prices = close_prices * (1 + np.abs(np.random.randn(100) * 0.01))
    low_prices = close_prices * (1 - np.abs(np.random.randn(100) * 0.01))
    volumes = np.random.randint(1000000, 10000000, 100)
    
    test_data = pd.DataFrame({
        'datetime': dates,
        'open': close_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })
    
    # 计算所有指标
    result = add_all_indicators(test_data)
    
    print(f"✅ 原始数据: {len(test_data.columns)} 列")
    print(f"✅ 添加指标后: {len(result.columns)} 列")
    print(f"✅ 新增指标: {len(result.columns) - len(test_data.columns)} 个")
    
    # 测试信号生成
    signals = get_trading_signal(result)
    buy_signals = (signals == 1).sum()
    sell_signals = (signals == -1).sum()
    
    print(f"✅ 买入信号: {buy_signals} 个")
    print(f"✅ 卖出信号: {sell_signals} 个")
    
    # 显示最新指标值
    latest = result.iloc[-1]
    print(f"\n📊 最新指标值:")
    print(f"   EMA8: {latest['ema_8']:.2f}")
    print(f"   EMA21: {latest['ema_21']:.2f}")
    print(f"   RSI: {latest['rsi']:.1f}")
    print(f"   MACD: {latest['macd']:.4f}")
    
    print("\n🎉 技术指标计算器测试完成!")


if __name__ == "__main__":
    test_indicators()
