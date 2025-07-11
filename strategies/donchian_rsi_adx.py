"""
唐奇安通道+RSI+ADX策略
基于唐奇安通道突破，结合RSI和ADX的趋势跟踪策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from .base_strategy import BaseStrategy

from .ta_indicators import RSI, ADX, PLUS_DI, MINUS_DI, MAX, MIN
TALIB_AVAILABLE = True

class DonchianRSIADXStrategy(BaseStrategy):
    """唐奇安通道+RSI+ADX策略"""
    
    def __init__(self, **params):
        super().__init__(**params)
        self.description = "基于唐奇安通道突破，结合RSI过滤和ADX趋势强度确认的策略"
    
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'donchian_period': 20,    # 唐奇安通道周期
            'rsi_period': 14,         # RSI周期
            'adx_period': 14,         # ADX周期
            'rsi_overbought': 70,     # RSI超买线
            'rsi_oversold': 30,       # RSI超卖线
            'adx_threshold': 25,      # ADX趋势强度阈值
            'breakout_threshold': 0.001,  # 突破确认阈值(0.1%)
        }
    
    def _custom_validate_params(self):
        """自定义参数验证"""
        if self.params['donchian_period'] < 5:
            raise ValueError("唐奇安通道周期不能小于5")
        
        if self.params['adx_threshold'] < 10 or self.params['adx_threshold'] > 50:
            raise ValueError("ADX阈值应在10-50之间")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # 计算唐奇安通道
        df['donchian_upper'] = MAX(df['high'].values, timeperiod=self.params['donchian_period'])
        df['donchian_lower'] = MIN(df['low'].values, timeperiod=self.params['donchian_period'])
        df['donchian_middle'] = (df['donchian_upper'] + df['donchian_lower']) / 2
        
        # 计算通道宽度
        df['donchian_width'] = (df['donchian_upper'] - df['donchian_lower']) / df['donchian_middle']
        
        # 计算RSI和ADX
        df['rsi'] = RSI(df['close'].values, timeperiod=self.params['rsi_period'])
        df['adx'] = ADX(df['high'].values, df['low'].values, df['close'].values, 
                        timeperiod=self.params['adx_period'])
        df['plus_di'] = PLUS_DI(df['high'].values, df['low'].values, df['close'].values,
                                timeperiod=self.params['adx_period'])
        df['minus_di'] = MINUS_DI(df['high'].values, df['low'].values, df['close'].values,
                                  timeperiod=self.params['adx_period'])
        
        # 计算价格相对于通道的位置
        df['price_position'] = (df['close'] - df['donchian_lower']) / (df['donchian_upper'] - df['donchian_lower'])
        
        # 计算突破强度
        df['upper_breakout_strength'] = (df['close'] - df['donchian_upper']) / df['donchian_upper']
        df['lower_breakout_strength'] = (df['donchian_lower'] - df['close']) / df['donchian_lower']
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """简化版ADX计算"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # 计算True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算方向移动
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # 平滑处理
        tr_smooth = tr.rolling(window=period).mean()
        plus_dm_smooth = plus_dm.rolling(window=period).mean()
        minus_dm_smooth = minus_dm.rolling(window=period).mean()
        
        # 计算DI
        plus_di = 100 * plus_dm_smooth / tr_smooth
        minus_di = 100 * minus_dm_smooth / tr_smooth
        
        # 计算ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['signal_strength'] = 0.0
        
        # 买入信号条件
        buy_condition = (
            # 价格突破唐奇安通道上轨
            (df['close'] > df['donchian_upper']) &
            (df['close'].shift(1) <= df['donchian_upper'].shift(1)) &
            # 突破强度足够
            (df['upper_breakout_strength'] > self.params['breakout_threshold']) &
            # RSI不超买
            (df['rsi'] < self.params['rsi_overbought']) &
            # ADX显示趋势强度足够
            (df['adx'] > self.params['adx_threshold']) &
            # +DI > -DI (多头趋势)
            (df['plus_di'] > df['minus_di'])
        )
        
        # 卖出信号条件
        sell_condition = (
            # 价格跌破唐奇安通道下轨
            (df['close'] < df['donchian_lower']) &
            (df['close'].shift(1) >= df['donchian_lower'].shift(1)) &
            # 突破强度足够
            (df['lower_breakout_strength'] > self.params['breakout_threshold']) &
            # RSI不超卖
            (df['rsi'] > self.params['rsi_oversold']) &
            # ADX显示趋势强度足够
            (df['adx'] > self.params['adx_threshold']) &
            # +DI < -DI (空头趋势)
            (df['plus_di'] < df['minus_di'])
        )
        
        # 设置信号
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # 计算信号强度
        df.loc[buy_condition, 'signal_strength'] = self._calculate_signal_strength(
            df.loc[buy_condition], signal_type='buy'
        )
        df.loc[sell_condition, 'signal_strength'] = self._calculate_signal_strength(
            df.loc[sell_condition], signal_type='sell'
        )
        
        # 计算持仓状态
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
        
        return df
    
    def _calculate_signal_strength(self, data: pd.DataFrame, signal_type: str) -> pd.Series:
        """计算信号强度"""
        if data.empty:
            return pd.Series(dtype=float)
        
        strength = pd.Series(0.4, index=data.index)  # 基础强度
        
        # 基于ADX强度调整
        adx_factor = np.clip((data['adx'] - 25) / 25, 0, 1)  # ADX 25-50为满强度
        strength += adx_factor * 0.3
        
        # 基于突破强度调整
        if signal_type == 'buy':
            breakout_factor = np.clip(data['upper_breakout_strength'] / 0.02, 0, 1)  # 2%为满强度
        else:
            breakout_factor = np.clip(data['lower_breakout_strength'] / 0.02, 0, 1)
        
        strength += breakout_factor * 0.2
        
        # 基于DI差值调整
        di_diff = abs(data['plus_di'] - data['minus_di'])
        di_factor = np.clip(di_diff / 20, 0, 1)  # DI差值20为满强度
        strength += di_factor * 0.1
        
        return np.clip(strength, 0, 1)
    
    def get_param_ranges(self) -> Dict[str, Tuple]:
        """获取参数优化范围"""
        return {
            'donchian_period': (10, 40, 5),
            'rsi_period': (10, 20, 2),
            'adx_period': (10, 20, 2),
            'adx_threshold': (20, 35, 5),
            'rsi_overbought': (65, 80, 5),
            'rsi_oversold': (20, 35, 5),
            'breakout_threshold': (0.0005, 0.005, 0.0005)
        }
    
    def get_strategy_description(self) -> str:
        """获取策略详细描述"""
        return f"""
        唐奇安通道+RSI+ADX策略详细说明:
        
        核心逻辑:
        1. 使用唐奇安通道({self.params['donchian_period']})识别突破点
        2. ADX({self.params['adx_period']})确认趋势强度
        3. RSI({self.params['rsi_period']})过滤超买超卖
        4. DI指标确认趋势方向
        
        买入条件:
        - 价格突破唐奇安通道上轨
        - 突破强度 > {self.params['breakout_threshold']:.1%}
        - RSI < {self.params['rsi_overbought']}
        - ADX > {self.params['adx_threshold']}(趋势强度足够)
        - +DI > -DI(多头趋势)
        
        卖出条件:
        - 价格跌破唐奇安通道下轨
        - 突破强度 > {self.params['breakout_threshold']:.1%}
        - RSI > {self.params['rsi_oversold']}
        - ADX > {self.params['adx_threshold']}
        - +DI < -DI(空头趋势)
        
        适用市场: 趋势突破行情
        风险提示: 在震荡市场中可能产生假突破
        """
