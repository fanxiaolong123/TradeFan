"""
策略模块
实现各种交易策略，主要以趋势策略为主
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, params: Dict, logger=None):
        self.params = params
        self.logger = logger
        self.name = self.__class__.__name__
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号
        
        Args:
            data: OHLCV数据
            
        Returns:
            信号序列: 1为买入，-1为卖出，0为持有
        """
        pass
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        计算技术指标
        
        Args:
            data: OHLCV数据
            
        Returns:
            指标字典
        """
        pass
    
    def get_latest_signal(self, data: pd.DataFrame) -> Tuple[int, Dict]:
        """
        获取最新信号和指标值
        
        Returns:
            (信号, 指标字典)
        """
        signals = self.generate_signals(data)
        indicators = self.calculate_indicators(data)
        
        if len(signals) == 0:
            return 0, {}
        
        latest_signal = signals.iloc[-1]
        latest_indicators = {k: v.iloc[-1] if len(v) > 0 else np.nan 
                           for k, v in indicators.items()}
        
        return int(latest_signal), latest_indicators

class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略
    结合移动平均线、ADX和唐奇安通道的综合趋势策略
    """
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        # 策略参数
        self.fast_ma = params.get('fast_ma', 20)
        self.slow_ma = params.get('slow_ma', 50)
        self.adx_period = params.get('adx_period', 14)
        self.adx_threshold = params.get('adx_threshold', 25)
        self.donchian_period = params.get('donchian_period', 20)
        
        if self.logger:
            self.logger.info(f"初始化趋势跟踪策略: MA({self.fast_ma},{self.slow_ma}) "
                           f"ADX({self.adx_period},{self.adx_threshold}) "
                           f"Donchian({self.donchian_period})")
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术指标"""
        indicators = {}
        
        try:
            # 移动平均线
            indicators['fast_ma'] = talib.SMA(data['close'].values, timeperiod=self.fast_ma)
            indicators['slow_ma'] = talib.SMA(data['close'].values, timeperiod=self.slow_ma)
            
            # ADX指标
            indicators['adx'] = talib.ADX(
                data['high'].values, 
                data['low'].values, 
                data['close'].values, 
                timeperiod=self.adx_period
            )
            
            # +DI和-DI
            indicators['plus_di'] = talib.PLUS_DI(
                data['high'].values, 
                data['low'].values, 
                data['close'].values, 
                timeperiod=self.adx_period
            )
            indicators['minus_di'] = talib.MINUS_DI(
                data['high'].values, 
                data['low'].values, 
                data['close'].values, 
                timeperiod=self.adx_period
            )
            
            # 唐奇安通道
            indicators['donchian_upper'] = data['high'].rolling(window=self.donchian_period).max()
            indicators['donchian_lower'] = data['low'].rolling(window=self.donchian_period).min()
            indicators['donchian_middle'] = (indicators['donchian_upper'] + indicators['donchian_lower']) / 2
            
            # RSI
            indicators['rsi'] = talib.RSI(data['close'].values, timeperiod=14)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(data['close'].values)
            indicators['macd'] = macd
            indicators['macd_signal'] = macd_signal
            indicators['macd_hist'] = macd_hist
            
            # 转换为pandas Series
            for key, value in indicators.items():
                if isinstance(value, np.ndarray):
                    indicators[key] = pd.Series(value, index=data.index)
                elif isinstance(value, pd.Series):
                    indicators[key] = value.reindex(data.index)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算技术指标失败: {e}")
            # 返回空指标
            for key in ['fast_ma', 'slow_ma', 'adx', 'plus_di', 'minus_di', 
                       'donchian_upper', 'donchian_lower', 'donchian_middle', 'rsi', 
                       'macd', 'macd_signal', 'macd_hist']:
                indicators[key] = pd.Series(index=data.index, dtype=float)
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < max(self.slow_ma, self.adx_period, self.donchian_period):
            return signals
        
        indicators = self.calculate_indicators(data)
        
        # 获取指标
        fast_ma = indicators['fast_ma']
        slow_ma = indicators['slow_ma']
        adx = indicators['adx']
        plus_di = indicators['plus_di']
        minus_di = indicators['minus_di']
        donchian_upper = indicators['donchian_upper']
        donchian_lower = indicators['donchian_lower']
        rsi = indicators['rsi']
        
        # 趋势条件
        uptrend = (fast_ma > slow_ma) & (adx > self.adx_threshold) & (plus_di > minus_di)
        downtrend = (fast_ma < slow_ma) & (adx > self.adx_threshold) & (plus_di < minus_di)
        
        # 突破条件
        breakout_up = data['close'] > donchian_upper.shift(1)
        breakout_down = data['close'] < donchian_lower.shift(1)
        
        # RSI过滤条件（避免超买超卖）
        rsi_ok_buy = rsi < 70
        rsi_ok_sell = rsi > 30
        
        # 生成信号
        buy_signal = uptrend & breakout_up & rsi_ok_buy
        sell_signal = downtrend & breakout_down & rsi_ok_sell
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals
    
    def get_signal_strength(self, data: pd.DataFrame) -> float:
        """获取信号强度（0-1之间）"""
        if len(data) < max(self.slow_ma, self.adx_period):
            return 0.0
        
        indicators = self.calculate_indicators(data)
        
        # ADX强度
        adx_strength = min(indicators['adx'].iloc[-1] / 50, 1.0) if not np.isnan(indicators['adx'].iloc[-1]) else 0
        
        # 移动平均线分离度
        ma_separation = abs(indicators['fast_ma'].iloc[-1] - indicators['slow_ma'].iloc[-1]) / indicators['slow_ma'].iloc[-1]
        ma_strength = min(ma_separation * 10, 1.0) if not np.isnan(ma_separation) else 0
        
        # 综合强度
        return (adx_strength + ma_strength) / 2

class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        self.fast_period = params.get('macd_fast', 12)
        self.slow_period = params.get('macd_slow', 26)
        self.signal_period = params.get('macd_signal', 9)
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算MACD指标"""
        indicators = {}
        
        try:
            macd, macd_signal, macd_hist = talib.MACD(
                data['close'].values,
                fastperiod=self.fast_period,
                slowperiod=self.slow_period,
                signalperiod=self.signal_period
            )
            
            indicators['macd'] = pd.Series(macd, index=data.index)
            indicators['macd_signal'] = pd.Series(macd_signal, index=data.index)
            indicators['macd_hist'] = pd.Series(macd_hist, index=data.index)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算MACD指标失败: {e}")
            for key in ['macd', 'macd_signal', 'macd_hist']:
                indicators[key] = pd.Series(index=data.index, dtype=float)
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成MACD交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < self.slow_period:
            return signals
        
        indicators = self.calculate_indicators(data)
        macd = indicators['macd']
        macd_signal = indicators['macd_signal']
        macd_hist = indicators['macd_hist']
        
        # MACD金叉死叉信号
        buy_signal = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
        sell_signal = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))
        
        # MACD柱状图信号
        hist_buy = (macd_hist > 0) & (macd_hist.shift(1) <= 0)
        hist_sell = (macd_hist < 0) & (macd_hist.shift(1) >= 0)
        
        # 综合信号
        signals[buy_signal | hist_buy] = 1
        signals[sell_signal | hist_sell] = -1
        
        return signals

class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        self.rsi_period = params.get('rsi_period', 14)
        self.oversold = params.get('rsi_oversold', 30)
        self.overbought = params.get('rsi_overbought', 70)
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算RSI指标"""
        indicators = {}
        
        try:
            rsi = talib.RSI(data['close'].values, timeperiod=self.rsi_period)
            indicators['rsi'] = pd.Series(rsi, index=data.index)
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算RSI指标失败: {e}")
            indicators['rsi'] = pd.Series(index=data.index, dtype=float)
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成RSI交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < self.rsi_period:
            return signals
        
        indicators = self.calculate_indicators(data)
        rsi = indicators['rsi']
        
        # RSI超买超卖信号
        buy_signal = (rsi < self.oversold) & (rsi.shift(1) >= self.oversold)
        sell_signal = (rsi > self.overbought) & (rsi.shift(1) <= self.overbought)
        
        signals[buy_signal] = 1
        signals[sell_signal] = -1
        
        return signals

class StrategyManager:
    """策略管理器"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.strategies = {}
    
    def add_strategy(self, name: str, strategy: BaseStrategy):
        """添加策略"""
        self.strategies[name] = strategy
        if self.logger:
            self.logger.info(f"添加策略: {name}")
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """获取策略"""
        return self.strategies.get(name)
    
    def get_all_signals(self, symbol: str, data: pd.DataFrame) -> Dict[str, Tuple[int, Dict]]:
        """获取所有策略的信号"""
        results = {}
        for name, strategy in self.strategies.items():
            try:
                signal, indicators = strategy.get_latest_signal(data)
                results[name] = (signal, indicators)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"策略{name}生成信号失败: {e}")
                results[name] = (0, {})
        return results
    
class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        # 策略参数
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.rsi_overbought = params.get('rsi_overbought', 70)
        self.bb_period = params.get('bb_period', 20)
        self.bb_std = params.get('bb_std', 2.0)
        
        if self.logger:
            self.logger.info(f"初始化均值回归策略: RSI({self.rsi_period},{self.rsi_oversold},{self.rsi_overbought}) BB({self.bb_period},{self.bb_std})")
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术指标"""
        indicators = {}
        
        try:
            # RSI指标
            rsi = talib.RSI(data['close'].values, timeperiod=self.rsi_period)
            indicators['rsi'] = pd.Series(rsi, index=data.index)
            
            # 布林带
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                data['close'].values, 
                timeperiod=self.bb_period, 
                nbdevup=self.bb_std, 
                nbdevdn=self.bb_std
            )
            indicators['bb_upper'] = pd.Series(bb_upper, index=data.index)
            indicators['bb_middle'] = pd.Series(bb_middle, index=data.index)
            indicators['bb_lower'] = pd.Series(bb_lower, index=data.index)
            
            # 布林带位置
            indicators['bb_position'] = (data['close'] - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
            
            # 价格相对于布林带中线的位置
            indicators['price_to_middle'] = (data['close'] - indicators['bb_middle']) / indicators['bb_middle']
            
            # 成交量移动平均
            indicators['volume_ma'] = data['volume'].rolling(window=20).mean()
            indicators['volume_ratio'] = data['volume'] / indicators['volume_ma']
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"指标计算失败: {e}")
            # 返回空指标
            for key in ['rsi', 'bb_upper', 'bb_middle', 'bb_lower', 'bb_position', 'price_to_middle', 'volume_ma', 'volume_ratio']:
                indicators[key] = pd.Series(index=data.index, dtype=float)
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < max(self.rsi_period, self.bb_period) + 10:
            return signals
        
        indicators = self.calculate_indicators(data)
        
        # 获取指标
        rsi = indicators['rsi']
        bb_upper = indicators['bb_upper']
        bb_lower = indicators['bb_lower']
        volume_ratio = indicators['volume_ratio']
        
        # 买入条件：超卖反转
        buy_condition = (
            (rsi < self.rsi_oversold) &  # RSI超卖
            (rsi > rsi.shift(1)) &  # RSI开始上升
            (data['close'] < bb_lower) &  # 价格在布林带下轨
            (volume_ratio > 1.2)  # 成交量放大
        )
        
        # 卖出条件：超买反转
        sell_condition = (
            (rsi > self.rsi_overbought) &  # RSI超买
            (rsi < rsi.shift(1)) &  # RSI开始下降
            (data['close'] > bb_upper) &  # 价格在布林带上轨
            (volume_ratio > 1.2)  # 成交量放大
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

class RangeStrategy(BaseStrategy):
    """震荡区间策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        # 策略参数
        self.lookback_period = params.get('lookback_period', 50)
        self.support_resistance_period = params.get('support_resistance_period', 20)
        self.breakout_threshold = params.get('breakout_threshold', 0.02)  # 2%突破阈值
        self.volume_threshold = params.get('volume_threshold', 1.5)
        
        if self.logger:
            self.logger.info(f"初始化震荡区间策略: 回看期({self.lookback_period}) 支撑阻力期({self.support_resistance_period})")
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术指标"""
        indicators = {}
        
        try:
            # 计算支撑和阻力位
            indicators['resistance'] = data['high'].rolling(window=self.support_resistance_period).max()
            indicators['support'] = data['low'].rolling(window=self.support_resistance_period).min()
            
            # 区间中位数
            indicators['range_middle'] = (indicators['resistance'] + indicators['support']) / 2
            
            # 区间宽度
            indicators['range_width'] = (indicators['resistance'] - indicators['support']) / indicators['range_middle']
            
            # 价格在区间中的位置 (0-1)
            indicators['range_position'] = (data['close'] - indicators['support']) / (indicators['resistance'] - indicators['support'])
            
            # ATR (平均真实波幅)
            atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
            indicators['atr'] = pd.Series(atr, index=data.index)
            
            # 成交量指标
            indicators['volume_ma'] = data['volume'].rolling(window=20).mean()
            indicators['volume_ratio'] = data['volume'] / indicators['volume_ma']
            
            # 价格波动率
            indicators['volatility'] = data['close'].rolling(window=20).std() / data['close'].rolling(window=20).mean()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"指标计算失败: {e}")
            # 返回空指标
            for key in ['resistance', 'support', 'range_middle', 'range_width', 'range_position', 'atr', 'volume_ma', 'volume_ratio', 'volatility']:
                indicators[key] = pd.Series(index=data.index, dtype=float)
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < self.lookback_period:
            return signals
        
        indicators = self.calculate_indicators(data)
        
        # 获取指标
        range_width = indicators['range_width']
        range_position = indicators['range_position']
        resistance = indicators['resistance']
        support = indicators['support']
        volume_ratio = indicators['volume_ratio']
        
        # 震荡区间内的交易
        in_range = range_width < 0.1  # 区间宽度小于10%
        
        # 买入条件：接近支撑位反弹
        buy_condition = (
            in_range &
            (range_position < 0.2) &  # 接近支撑位
            (data['close'] > data['close'].shift(1)) &  # 价格开始反弹
            (volume_ratio > self.volume_threshold)  # 成交量放大
        )
        
        # 卖出条件：接近阻力位回落
        sell_condition = (
            in_range &
            (range_position > 0.8) &  # 接近阻力位
            (data['close'] < data['close'].shift(1)) &  # 价格开始回落
            (volume_ratio > self.volume_threshold)  # 成交量放大
        )
        
        # 突破交易
        breakout_up = (
            (data['close'] > resistance * (1 + self.breakout_threshold)) &
            (volume_ratio > self.volume_threshold * 1.5)
        )
        
        breakout_down = (
            (data['close'] < support * (1 - self.breakout_threshold)) &
            (volume_ratio > self.volume_threshold * 1.5)
        )
        
        signals[buy_condition | breakout_up] = 1
        signals[sell_condition | breakout_down] = -1
        
        return signals

    def create_strategy(self, strategy_type: str, params: Dict) -> BaseStrategy:
        """创建策略实例"""
        strategy_classes = {
            'TrendFollowing': TrendFollowingStrategy,
            'MACD': MACDStrategy,
            'RSI': RSIStrategy,
            'MeanReversion': MeanReversionStrategy,
            'Range': RangeStrategy
        }
        
        if strategy_type not in strategy_classes:
            raise ValueError(f"不支持的策略类型: {strategy_type}")
        
        return strategy_classes[strategy_type](params, self.logger)
