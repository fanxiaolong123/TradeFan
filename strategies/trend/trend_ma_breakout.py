"""
趋势MA突破策略
基于移动平均线交叉的趋势跟踪策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from .base_strategy import BaseStrategy

from .ta_indicators import MA, RSI, ADX, PLUS_DI, MINUS_DI, MAX, MIN
TALIB_AVAILABLE = True

class TrendMABreakoutStrategy(BaseStrategy):
    """趋势MA突破策略"""
    
    def __init__(self, **params):
        super().__init__(**params)
        self.description = "基于快慢移动平均线交叉的趋势跟踪策略，结合RSI过滤"
    
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'fast_ma': 20,      # 快速移动平均周期
            'slow_ma': 50,      # 慢速移动平均周期
            'rsi_period': 14,   # RSI周期
            'rsi_overbought': 70,  # RSI超买线
            'rsi_oversold': 30,    # RSI超卖线
            'ma_type': 'SMA',   # MA类型: SMA, EMA
            'min_trend_strength': 0.01,  # 最小趋势强度
        }
    
    def _custom_validate_params(self):
        """自定义参数验证"""
        if self.params['fast_ma'] >= self.params['slow_ma']:
            raise ValueError("快速MA周期必须小于慢速MA周期")
        
        if not (0 < self.params['rsi_overbought'] <= 100):
            raise ValueError("RSI超买线必须在0-100之间")
        
        if not (0 <= self.params['rsi_oversold'] < 100):
            raise ValueError("RSI超卖线必须在0-100之间")
        
        if self.params['rsi_oversold'] >= self.params['rsi_overbought']:
            raise ValueError("RSI超卖线必须小于超买线")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # 计算移动平均线
        if self.params['ma_type'] == 'EMA':
            df['fast_ma'] = MA(df['close'].values, timeperiod=self.params['fast_ma'], matype=1)
            df['slow_ma'] = MA(df['close'].values, timeperiod=self.params['slow_ma'], matype=1)
        else:
            df['fast_ma'] = MA(df['close'].values, timeperiod=self.params['fast_ma'], matype=0)
            df['slow_ma'] = MA(df['close'].values, timeperiod=self.params['slow_ma'], matype=0)
        
        # 计算RSI
        df['rsi'] = RSI(df['close'].values, timeperiod=self.params['rsi_period'])
        
        # 计算MA差值和趋势强度
        df['ma_diff'] = df['fast_ma'] - df['slow_ma']
        df['ma_diff_pct'] = df['ma_diff'] / df['slow_ma']
        
        # 计算趋势强度
        df['trend_strength'] = abs(df['ma_diff_pct'])
        
        # 计算价格相对于MA的位置
        df['price_vs_fast_ma'] = (df['close'] - df['fast_ma']) / df['fast_ma']
        df['price_vs_slow_ma'] = (df['close'] - df['slow_ma']) / df['slow_ma']
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['signal_strength'] = 0.0
        
        # 生成买入信号条件
        buy_condition = (
            # MA金叉：快线上穿慢线
            (df['fast_ma'] > df['slow_ma']) & 
            (df['fast_ma'].shift(1) <= df['slow_ma'].shift(1)) &
            # RSI不超买
            (df['rsi'] < self.params['rsi_overbought']) &
            # 趋势强度足够
            (df['trend_strength'] > self.params['min_trend_strength']) &
            # 价格在快线上方（确认突破）
            (df['close'] > df['fast_ma'])
        )
        
        # 生成卖出信号条件
        sell_condition = (
            # MA死叉：快线下穿慢线
            (df['fast_ma'] < df['slow_ma']) & 
            (df['fast_ma'].shift(1) >= df['slow_ma'].shift(1)) &
            # RSI不超卖
            (df['rsi'] > self.params['rsi_oversold']) &
            # 趋势强度足够
            (df['trend_strength'] > self.params['min_trend_strength'])
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
        
        strength = pd.Series(0.5, index=data.index)  # 基础强度
        
        # 基于趋势强度调整
        trend_factor = np.clip(data['trend_strength'] / 0.05, 0, 1)  # 5%为满强度
        strength += trend_factor * 0.3
        
        # 基于RSI位置调整
        if signal_type == 'buy':
            # 买入时，RSI越低越好
            rsi_factor = (70 - data['rsi']) / 40  # RSI在30-70之间标准化
        else:
            # 卖出时，RSI越高越好
            rsi_factor = (data['rsi'] - 30) / 40
        
        rsi_factor = np.clip(rsi_factor, 0, 1)
        strength += rsi_factor * 0.2
        
        return np.clip(strength, 0, 1)
    
    def get_param_ranges(self) -> Dict[str, Tuple]:
        """获取参数优化范围"""
        return {
            'fast_ma': (5, 30, 1),
            'slow_ma': (20, 100, 5),
            'rsi_period': (10, 20, 2),
            'rsi_overbought': (65, 80, 5),
            'rsi_oversold': (20, 35, 5),
            'min_trend_strength': (0.005, 0.03, 0.005)
        }
    
    def get_signal_strength(self, data: pd.DataFrame, index: int) -> float:
        """获取指定位置的信号强度"""
        if 'signal_strength' in data.columns and index < len(data):
            return data.iloc[index]['signal_strength']
        return 0.0
    
    def get_strategy_description(self) -> str:
        """获取策略详细描述"""
        return f"""
        趋势MA突破策略详细说明:
        
        核心逻辑:
        1. 使用快速MA({self.params['fast_ma']})和慢速MA({self.params['slow_ma']})识别趋势
        2. 金叉时买入，死叉时卖出
        3. 使用RSI({self.params['rsi_period']})过滤超买超卖区域
        4. 要求最小趋势强度({self.params['min_trend_strength']:.1%})避免震荡市场
        
        买入条件:
        - 快线上穿慢线(金叉)
        - RSI < {self.params['rsi_overbought']}(避免超买)
        - 趋势强度 > {self.params['min_trend_strength']:.1%}
        - 价格在快线上方(确认突破)
        
        卖出条件:
        - 快线下穿慢线(死叉)
        - RSI > {self.params['rsi_oversold']}(避免超卖)
        - 趋势强度 > {self.params['min_trend_strength']:.1%}
        
        适用市场: 趋势性较强的市场
        风险提示: 在震荡市场中可能产生较多假信号
        """
