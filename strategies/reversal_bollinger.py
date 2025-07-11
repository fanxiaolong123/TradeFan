"""
布林带反转策略
基于布林带的均值回归策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from .base_strategy import BaseStrategy

from .ta_indicators import BOLLINGER_BANDS, RSI, STOCH
TALIB_AVAILABLE = True

class ReversalBollingerStrategy(BaseStrategy):
    """布林带反转策略"""
    
    def __init__(self, **params):
        super().__init__(**params)
        self.description = "基于布林带的均值回归策略，在极端位置寻找反转机会"
    
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'bb_period': 20,          # 布林带周期
            'bb_std': 2.0,           # 布林带标准差倍数
            'rsi_period': 14,        # RSI周期
            'rsi_overbought': 80,    # RSI超买线(反转策略用更极端值)
            'rsi_oversold': 20,      # RSI超卖线
            'volume_factor': 1.2,    # 成交量放大倍数
            'min_bb_width': 0.02,    # 最小布林带宽度(2%)
        }
    
    def _custom_validate_params(self):
        """自定义参数验证"""
        if self.params['bb_std'] < 1.0 or self.params['bb_std'] > 3.0:
            raise ValueError("布林带标准差倍数应在1.0-3.0之间")
        
        if self.params['volume_factor'] < 1.0:
            raise ValueError("成交量放大倍数不能小于1.0")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # 计算布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = BOLLINGER_BANDS(
            df['close'].values, 
            timeperiod=self.params['bb_period'],
            nbdevup=self.params['bb_std'],
            nbdevdn=self.params['bb_std']
        )
        
        # 计算RSI
        df['rsi'] = RSI(df['close'].values, timeperiod=self.params['rsi_period'])
        
        # 计算布林带相关指标
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 计算价格相对于布林带的位置
        df['price_vs_upper'] = (df['close'] - df['bb_upper']) / df['bb_upper']
        df['price_vs_lower'] = (df['bb_lower'] - df['close']) / df['bb_lower']
        
        # 计算成交量指标
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # 计算波动率
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
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
        
        # 买入信号条件(超卖反转)
        buy_condition = (
            # 价格触及或跌破布林带下轨
            (df['close'] <= df['bb_lower']) &
            # RSI超卖
            (df['rsi'] < self.params['rsi_oversold']) &
            # 布林带宽度足够(避免盘整)
            (df['bb_width'] > self.params['min_bb_width']) &
            # 成交量放大(确认反转)
            (df['volume_ratio'] > self.params['volume_factor']) &
            # 价格开始反弹
            (df['close'] > df['close'].shift(1))
        )
        
        # 卖出信号条件(超买反转)
        sell_condition = (
            # 价格触及或突破布林带上轨
            (df['close'] >= df['bb_upper']) &
            # RSI超买
            (df['rsi'] > self.params['rsi_overbought']) &
            # 布林带宽度足够
            (df['bb_width'] > self.params['min_bb_width']) &
            # 成交量放大
            (df['volume_ratio'] > self.params['volume_factor']) &
            # 价格开始回落
            (df['close'] < df['close'].shift(1))
        )
        
        # 平仓条件(回归中轨)
        close_long_condition = (
            (df['position'].shift(1) == 1) &  # 当前持多头
            (df['close'] >= df['bb_middle'])  # 价格回到中轨附近
        )
        
        close_short_condition = (
            (df['position'].shift(1) == -1) &  # 当前持空头
            (df['close'] <= df['bb_middle'])   # 价格回到中轨附近
        )
        
        # 设置信号
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        df.loc[close_long_condition | close_short_condition, 'signal'] = 0
        
        # 计算信号强度
        df.loc[buy_condition, 'signal_strength'] = self._calculate_signal_strength(
            df.loc[buy_condition], signal_type='buy'
        )
        df.loc[sell_condition, 'signal_strength'] = self._calculate_signal_strength(
            df.loc[sell_condition], signal_type='sell'
        )
        
        # 计算持仓状态(反转策略需要特殊处理)
        position = 0
        positions = []
        for i, row in df.iterrows():
            if row['signal'] == 1:
                position = 1
            elif row['signal'] == -1:
                position = -1
            elif row['signal'] == 0 and position != 0:
                position = 0
            positions.append(position)
        
        df['position'] = positions
        
        return df
    
    def _calculate_signal_strength(self, data: pd.DataFrame, signal_type: str) -> pd.Series:
        """计算信号强度"""
        if data.empty:
            return pd.Series(dtype=float)
        
        strength = pd.Series(0.4, index=data.index)  # 基础强度
        
        # 基于RSI极端程度调整
        if signal_type == 'buy':
            rsi_factor = np.clip((20 - data['rsi']) / 20, 0, 1)  # RSI越低强度越高
            bb_factor = np.clip(-data['price_vs_lower'] / 0.02, 0, 1)  # 跌破下轨越多强度越高
        else:
            rsi_factor = np.clip((data['rsi'] - 80) / 20, 0, 1)  # RSI越高强度越高
            bb_factor = np.clip(data['price_vs_upper'] / 0.02, 0, 1)  # 突破上轨越多强度越高
        
        strength += rsi_factor * 0.3
        strength += bb_factor * 0.2
        
        # 基于成交量放大程度调整
        volume_factor = np.clip((data['volume_ratio'] - 1) / 2, 0, 1)  # 成交量放大3倍为满强度
        strength += volume_factor * 0.1
        
        return np.clip(strength, 0, 1)
    
    def get_param_ranges(self) -> Dict[str, Tuple]:
        """获取参数优化范围"""
        return {
            'bb_period': (10, 30, 5),
            'bb_std': (1.5, 2.5, 0.1),
            'rsi_period': (10, 20, 2),
            'rsi_overbought': (75, 85, 2),
            'rsi_oversold': (15, 25, 2),
            'volume_factor': (1.0, 2.0, 0.2),
            'min_bb_width': (0.01, 0.05, 0.005)
        }
    
    def should_exit_position(self, current_price: float, entry_price: float, 
                           position_side: int, risk_params: Dict) -> Tuple[bool, str]:
        """重写退出逻辑，反转策略有不同的退出条件"""
        if entry_price <= 0:
            return False, ""
        
        # 计算盈亏比例
        if position_side == 1:  # 多头
            pnl_ratio = (current_price - entry_price) / entry_price
        else:  # 空头
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 反转策略的止损相对宽松
        stop_loss = risk_params.get('stop_loss', 0.03)  # 3%止损
        if pnl_ratio <= -stop_loss:
            return True, f"止损触发 (亏损{pnl_ratio:.2%})"
        
        # 反转策略的止盈相对保守
        take_profit = risk_params.get('take_profit', 0.02)  # 2%止盈
        if pnl_ratio >= take_profit:
            return True, f"止盈触发 (盈利{pnl_ratio:.2%})"
        
        return False, ""
    
    def get_strategy_description(self) -> str:
        """获取策略详细描述"""
        return f"""
        布林带反转策略详细说明:
        
        核心逻辑:
        1. 使用布林带({self.params['bb_period']}, {self.params['bb_std']})识别极端价格
        2. 在极端位置寻找反转机会
        3. 使用RSI确认超买超卖状态
        4. 成交量放大确认反转信号
        
        买入条件(超卖反转):
        - 价格触及或跌破布林带下轨
        - RSI < {self.params['rsi_oversold']}(超卖)
        - 布林带宽度 > {self.params['min_bb_width']:.1%}(避免盘整)
        - 成交量放大 > {self.params['volume_factor']}倍
        - 价格开始反弹
        
        卖出条件(超买反转):
        - 价格触及或突破布林带上轨
        - RSI > {self.params['rsi_overbought']}(超买)
        - 布林带宽度 > {self.params['min_bb_width']:.1%}
        - 成交量放大 > {self.params['volume_factor']}倍
        - 价格开始回落
        
        平仓条件:
        - 价格回归布林带中轨附近
        
        适用市场: 震荡市场，有明确支撑阻力的市场
        风险提示: 在强趋势市场中可能逆势操作
        """
