"""
专业短线交易策略 (Scalping Strategy)
针对5分钟-1小时级别优化的高频交易策略

特点:
1. 多时间框架分析
2. 高精度入场/出场时机
3. 动态止损止盈
4. 成交量确认
5. 市场微观结构分析
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .base_strategy import BaseStrategy
from .ta_indicators import (
    EMA, SMA, RSI, MACD, BOLLINGER_BANDS, ATR, 
    STOCH, WILLIAMS_R, CCI, MFI, OBV, VWAP
)

class ScalpingStrategy(BaseStrategy):
    """专业短线交易策略"""
    
    def __init__(self, **params):
        super().__init__(**params)
        self.description = "专业短线交易策略，适用于5分钟-1小时级别"
        self.timeframes = ['5m', '15m', '30m', '1h']
        self.signal_history = []
        self.last_signal_time = None
        
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            # 移动平均线参数
            'ema_fast': 8,          # 快速EMA
            'ema_medium': 21,       # 中速EMA
            'ema_slow': 55,         # 慢速EMA
            
            # 布林带参数
            'bb_period': 20,        # 布林带周期
            'bb_std': 2.0,          # 布林带标准差
            
            # RSI参数
            'rsi_period': 14,       # RSI周期
            'rsi_overbought': 75,   # RSI超买线
            'rsi_oversold': 25,     # RSI超卖线
            
            # MACD参数
            'macd_fast': 12,        # MACD快线
            'macd_slow': 26,        # MACD慢线
            'macd_signal': 9,       # MACD信号线
            
            # 随机指标参数
            'stoch_k': 14,          # %K周期
            'stoch_d': 3,           # %D周期
            'stoch_overbought': 80, # 随机指标超买
            'stoch_oversold': 20,   # 随机指标超卖
            
            # 成交量参数
            'volume_ma': 20,        # 成交量移动平均
            'volume_threshold': 1.5, # 成交量放大倍数
            
            # ATR参数
            'atr_period': 14,       # ATR周期
            'atr_multiplier': 2.0,  # ATR止损倍数
            
            # 信号过滤参数
            'min_signal_interval': 3,    # 最小信号间隔(根)
            'trend_filter': True,        # 是否启用趋势过滤
            'volume_filter': True,       # 是否启用成交量过滤
            'volatility_filter': True,   # 是否启用波动率过滤
            
            # 风险控制参数
            'max_risk_per_trade': 0.01,  # 单笔最大风险1%
            'dynamic_stop_loss': True,   # 动态止损
            'profit_target_ratio': 2.0,  # 盈亏比
        }
    
    def _custom_validate_params(self):
        """自定义参数验证"""
        if self.params['ema_fast'] >= self.params['ema_medium']:
            raise ValueError("快速EMA必须小于中速EMA")
        if self.params['ema_medium'] >= self.params['ema_slow']:
            raise ValueError("中速EMA必须小于慢速EMA")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        df = data.copy()
        
        # 移动平均线
        df['ema_fast'] = EMA(df['close'], self.params['ema_fast'])
        df['ema_medium'] = EMA(df['close'], self.params['ema_medium'])
        df['ema_slow'] = EMA(df['close'], self.params['ema_slow'])
        
        # 布林带
        bb_upper, bb_middle, bb_lower = BOLLINGER_BANDS(
            df['close'], 
            self.params['bb_period'], 
            self.params['bb_std']
        )
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        df['bb_width'] = (bb_upper - bb_lower) / bb_middle
        df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # RSI
        df['rsi'] = RSI(df['close'], self.params['rsi_period'])
        
        # MACD
        macd_line, macd_signal, macd_hist = MACD(
            df['close'],
            self.params['macd_fast'],
            self.params['macd_slow'],
            self.params['macd_signal']
        )
        df['macd'] = macd_line
        df['macd_signal'] = macd_signal
        df['macd_hist'] = macd_hist
        
        # 随机指标
        stoch_k, stoch_d = STOCH(
            df['high'], df['low'], df['close'],
            self.params['stoch_k'], self.params['stoch_d']
        )
        df['stoch_k'] = stoch_k
        df['stoch_d'] = stoch_d
        
        # ATR (波动率)
        df['atr'] = ATR(df['high'], df['low'], df['close'], self.params['atr_period'])
        
        # 成交量指标
        df['volume_ma'] = SMA(df['volume'], self.params['volume_ma'])
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 价格动量
        df['price_momentum'] = df['close'].pct_change(5)  # 5期价格动量
        
        # 趋势强度
        df['trend_strength'] = self._calculate_trend_strength(df)
        
        # 市场微观结构
        df = self._calculate_microstructure(df)
        
        return df
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """计算趋势强度"""
        # 基于EMA排列计算趋势强度
        ema_alignment = np.where(
            (df['ema_fast'] > df['ema_medium']) & (df['ema_medium'] > df['ema_slow']), 1,
            np.where(
                (df['ema_fast'] < df['ema_medium']) & (df['ema_medium'] < df['ema_slow']), -1, 0
            )
        )
        
        # 结合价格相对于EMA的位置
        price_position = (df['close'] - df['ema_medium']) / df['ema_medium']
        
        # 综合趋势强度
        trend_strength = ema_alignment * np.abs(price_position) * 100
        
        return pd.Series(trend_strength, index=df.index)
    
    def _calculate_microstructure(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算市场微观结构指标"""
        # 买卖压力
        df['buying_pressure'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['selling_pressure'] = (df['high'] - df['close']) / (df['high'] - df['low'])
        
        # 价格效率
        df['price_efficiency'] = np.abs(df['close'] - df['open']) / (df['high'] - df['low'])
        
        # 成交量加权价格
        df['vwap'] = VWAP(df['high'], df['low'], df['close'], df['volume'])
        df['vwap_deviation'] = (df['close'] - df['vwap']) / df['vwap']
        
        return df
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        df['signal'] = 0
        df['signal_strength'] = 0.0
        df['entry_reason'] = ''
        df['exit_reason'] = ''
        
        # 计算各种信号组件
        trend_signals = self._get_trend_signals(df)
        momentum_signals = self._get_momentum_signals(df)
        mean_reversion_signals = self._get_mean_reversion_signals(df)
        volume_signals = self._get_volume_signals(df)
        
        # 综合信号
        for i in range(len(df)):
            if i < max(self.params['ema_slow'], self.params['bb_period']):
                continue
                
            # 检查信号间隔
            if not self._check_signal_interval(i):
                continue
            
            # 多头信号
            long_score = self._calculate_long_score(
                df, i, trend_signals, momentum_signals, 
                mean_reversion_signals, volume_signals
            )
            
            # 空头信号
            short_score = self._calculate_short_score(
                df, i, trend_signals, momentum_signals, 
                mean_reversion_signals, volume_signals
            )
            
            # 应用过滤器
            if self._apply_filters(df, i, long_score, short_score):
                if long_score > 0.6:  # 强多头信号
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'signal_strength'] = long_score
                    df.loc[df.index[i], 'entry_reason'] = self._get_entry_reason(df, i, 'long')
                elif short_score > 0.6:  # 强空头信号
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'signal_strength'] = short_score
                    df.loc[df.index[i], 'entry_reason'] = self._get_entry_reason(df, i, 'short')
        
        # 计算动态止损止盈
        df = self._calculate_dynamic_stops(df)
        
        return df
    
    def _get_trend_signals(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """获取趋势信号"""
        signals = {}
        
        # EMA交叉信号
        signals['ema_cross_bull'] = (
            (df['ema_fast'] > df['ema_medium']) & 
            (df['ema_fast'].shift(1) <= df['ema_medium'].shift(1))
        )
        signals['ema_cross_bear'] = (
            (df['ema_fast'] < df['ema_medium']) & 
            (df['ema_fast'].shift(1) >= df['ema_medium'].shift(1))
        )
        
        # 价格突破EMA
        signals['price_above_emas'] = (
            (df['close'] > df['ema_fast']) & 
            (df['close'] > df['ema_medium'])
        )
        signals['price_below_emas'] = (
            (df['close'] < df['ema_fast']) & 
            (df['close'] < df['ema_medium'])
        )
        
        return signals
    
    def _get_momentum_signals(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """获取动量信号"""
        signals = {}
        
        # MACD信号
        signals['macd_bull'] = (
            (df['macd'] > df['macd_signal']) & 
            (df['macd_hist'] > 0)
        )
        signals['macd_bear'] = (
            (df['macd'] < df['macd_signal']) & 
            (df['macd_hist'] < 0)
        )
        
        # RSI信号
        signals['rsi_bull'] = (
            (df['rsi'] > 50) & 
            (df['rsi'] < self.params['rsi_overbought'])
        )
        signals['rsi_bear'] = (
            (df['rsi'] < 50) & 
            (df['rsi'] > self.params['rsi_oversold'])
        )
        
        # 随机指标信号
        signals['stoch_bull'] = (
            (df['stoch_k'] > df['stoch_d']) & 
            (df['stoch_k'] < self.params['stoch_overbought'])
        )
        signals['stoch_bear'] = (
            (df['stoch_k'] < df['stoch_d']) & 
            (df['stoch_k'] > self.params['stoch_oversold'])
        )
        
        return signals
    
    def _get_mean_reversion_signals(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """获取均值回归信号"""
        signals = {}
        
        # 布林带信号
        signals['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).quantile(0.2)
        signals['bb_expansion'] = df['bb_width'] > df['bb_width'].rolling(20).quantile(0.8)
        
        signals['bb_lower_touch'] = (
            (df['low'] <= df['bb_lower']) & 
            (df['close'] > df['bb_lower'])
        )
        signals['bb_upper_touch'] = (
            (df['high'] >= df['bb_upper']) & 
            (df['close'] < df['bb_upper'])
        )
        
        return signals
    
    def _get_volume_signals(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """获取成交量信号"""
        signals = {}
        
        # 成交量放大
        signals['volume_surge'] = df['volume_ratio'] > self.params['volume_threshold']
        
        # 成交量趋势
        signals['volume_trend_up'] = df['volume_ma'] > df['volume_ma'].shift(5)
        signals['volume_trend_down'] = df['volume_ma'] < df['volume_ma'].shift(5)
        
        return signals
    
    def _calculate_long_score(self, df: pd.DataFrame, i: int, 
                            trend_signals: Dict, momentum_signals: Dict,
                            mean_reversion_signals: Dict, volume_signals: Dict) -> float:
        """计算多头信号得分"""
        score = 0.0
        
        # 趋势得分 (40%)
        if trend_signals['ema_cross_bull'].iloc[i]:
            score += 0.15
        if trend_signals['price_above_emas'].iloc[i]:
            score += 0.15
        if df['trend_strength'].iloc[i] > 0:
            score += 0.10
        
        # 动量得分 (30%)
        if momentum_signals['macd_bull'].iloc[i]:
            score += 0.10
        if momentum_signals['rsi_bull'].iloc[i]:
            score += 0.10
        if momentum_signals['stoch_bull'].iloc[i]:
            score += 0.10
        
        # 均值回归得分 (20%)
        if mean_reversion_signals['bb_lower_touch'].iloc[i]:
            score += 0.15
        if df['bb_position'].iloc[i] < 0.3:  # 接近下轨
            score += 0.05
        
        # 成交量得分 (10%)
        if volume_signals['volume_surge'].iloc[i]:
            score += 0.05
        if volume_signals['volume_trend_up'].iloc[i]:
            score += 0.05
        
        return min(score, 1.0)
    
    def _calculate_short_score(self, df: pd.DataFrame, i: int,
                             trend_signals: Dict, momentum_signals: Dict,
                             mean_reversion_signals: Dict, volume_signals: Dict) -> float:
        """计算空头信号得分"""
        score = 0.0
        
        # 趋势得分 (40%)
        if trend_signals['ema_cross_bear'].iloc[i]:
            score += 0.15
        if trend_signals['price_below_emas'].iloc[i]:
            score += 0.15
        if df['trend_strength'].iloc[i] < 0:
            score += 0.10
        
        # 动量得分 (30%)
        if momentum_signals['macd_bear'].iloc[i]:
            score += 0.10
        if momentum_signals['rsi_bear'].iloc[i]:
            score += 0.10
        if momentum_signals['stoch_bear'].iloc[i]:
            score += 0.10
        
        # 均值回归得分 (20%)
        if mean_reversion_signals['bb_upper_touch'].iloc[i]:
            score += 0.15
        if df['bb_position'].iloc[i] > 0.7:  # 接近上轨
            score += 0.05
        
        # 成交量得分 (10%)
        if volume_signals['volume_surge'].iloc[i]:
            score += 0.05
        if volume_signals['volume_trend_up'].iloc[i]:
            score += 0.05
        
        return min(score, 1.0)
    
    def _apply_filters(self, df: pd.DataFrame, i: int, 
                      long_score: float, short_score: float) -> bool:
        """应用信号过滤器"""
        # 趋势过滤
        if self.params['trend_filter']:
            if abs(df['trend_strength'].iloc[i]) < 10:  # 趋势太弱
                return False
        
        # 波动率过滤
        if self.params['volatility_filter']:
            if df['atr'].iloc[i] < df['atr'].rolling(20).mean().iloc[i] * 0.5:
                return False  # 波动率太低
        
        # 成交量过滤
        if self.params['volume_filter']:
            if df['volume_ratio'].iloc[i] < 0.8:  # 成交量太低
                return False
        
        return True
    
    def _check_signal_interval(self, i: int) -> bool:
        """检查信号间隔"""
        if len(self.signal_history) == 0:
            return True
        
        last_signal_index = self.signal_history[-1] if self.signal_history else -999
        return i - last_signal_index >= self.params['min_signal_interval']
    
    def _get_entry_reason(self, df: pd.DataFrame, i: int, direction: str) -> str:
        """获取入场原因"""
        reasons = []
        
        if direction == 'long':
            if df['ema_fast'].iloc[i] > df['ema_medium'].iloc[i]:
                reasons.append("EMA多头排列")
            if df['macd_hist'].iloc[i] > 0:
                reasons.append("MACD金叉")
            if df['rsi'].iloc[i] > 50:
                reasons.append("RSI强势")
        else:
            if df['ema_fast'].iloc[i] < df['ema_medium'].iloc[i]:
                reasons.append("EMA空头排列")
            if df['macd_hist'].iloc[i] < 0:
                reasons.append("MACD死叉")
            if df['rsi'].iloc[i] < 50:
                reasons.append("RSI弱势")
        
        return "; ".join(reasons)
    
    def _calculate_dynamic_stops(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算动态止损止盈"""
        df['dynamic_stop_loss'] = 0.0
        df['dynamic_take_profit'] = 0.0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] != 0:
                atr_value = df['atr'].iloc[i]
                current_price = df['close'].iloc[i]
                
                if df['signal'].iloc[i] == 1:  # 多头
                    stop_loss = current_price - (atr_value * self.params['atr_multiplier'])
                    take_profit = current_price + (atr_value * self.params['atr_multiplier'] * self.params['profit_target_ratio'])
                else:  # 空头
                    stop_loss = current_price + (atr_value * self.params['atr_multiplier'])
                    take_profit = current_price - (atr_value * self.params['atr_multiplier'] * self.params['profit_target_ratio'])
                
                df.loc[df.index[i], 'dynamic_stop_loss'] = stop_loss
                df.loc[df.index[i], 'dynamic_take_profit'] = take_profit
        
        return df
    
    def get_param_ranges(self) -> Dict[str, Tuple]:
        """获取参数优化范围"""
        return {
            'ema_fast': (5, 15, 1),
            'ema_medium': (15, 30, 1),
            'ema_slow': (40, 70, 5),
            'bb_period': (15, 25, 1),
            'bb_std': (1.5, 2.5, 0.1),
            'rsi_period': (10, 20, 1),
            'atr_multiplier': (1.5, 3.0, 0.1),
            'profit_target_ratio': (1.5, 3.0, 0.1),
        }
    
    def get_signal_strength(self, data: pd.DataFrame, index: int) -> float:
        """获取信号强度"""
        if 'signal_strength' in data.columns:
            return data['signal_strength'].iloc[index]
        return 1.0
    
    def calculate_position_size(self, signal: int, current_price: float, 
                              available_capital: float, risk_params: Dict) -> float:
        """计算仓位大小 - 基于ATR的风险调整"""
        if signal == 0:
            return 0
        
        # 获取ATR值
        atr_value = risk_params.get('atr', current_price * 0.02)  # 默认2%
        
        # 计算风险金额
        risk_amount = available_capital * self.params['max_risk_per_trade']
        
        # 计算止损距离
        stop_distance = atr_value * self.params['atr_multiplier']
        
        # 计算仓位大小
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            return min(position_size, available_capital * 0.2 / current_price)  # 最大20%仓位
        
        return 0
