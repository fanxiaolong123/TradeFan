"""
TradeFan 趋势跟踪策略
专业的趋势跟踪系统，支持多时间框架分析和动态参数调整

策略特点:
- 多重EMA系统确认趋势
- ADX强度过滤
- MACD动量确认
- ATR动态止损
- 支持做多和做空
- 自适应参数调整
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

try:
    from .base_strategy import BaseStrategy
    from indicators_lib import trend, momentum, volatility, composite
except ImportError:
    # 用于直接运行测试
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from strategies.base_strategy import BaseStrategy
    from indicators_lib import trend, momentum, volatility, composite


class TrendFollowingStrategy(BaseStrategy):
    """趋势跟踪策略"""
    
    def __init__(self, config: Dict = None):
        # 使用默认配置如果没有提供配置
        if config is None:
            config = DEFAULT_TREND_CONFIG.copy()
        
        # 调用父类构造函数
        super().__init__(**config)
        
        self.name = "TrendFollowingStrategy"
        self.logger = logging.getLogger(__name__)
        
        # 核心参数 - 从params中获取
        self.ema_fast = self.params.get('ema_fast', 8)
        self.ema_medium = self.params.get('ema_medium', 21)
        self.ema_slow = self.params.get('ema_slow', 55)
        
        # 趋势确认参数
        self.adx_period = self.params.get('adx_period', 14)
        self.adx_threshold = self.params.get('adx_threshold', 25)
        
        # 动量确认参数
        self.macd_fast = self.params.get('macd_fast', 12)
        self.macd_slow = self.params.get('macd_slow', 26)
        self.macd_signal = self.params.get('macd_signal', 9)
        
        # 波动率参数
        self.atr_period = self.params.get('atr_period', 14)
        self.atr_multiplier = self.params.get('atr_multiplier', 2.0)
        
        # 过滤参数
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_overbought = self.params.get('rsi_overbought', 80)
        self.rsi_oversold = self.params.get('rsi_oversold', 20)
        
        # 趋势强度参数
        self.trend_strength_threshold = self.params.get('trend_strength_threshold', 0.6)
        
        # 风险管理参数
        self.max_risk_per_trade = self.params.get('max_risk_per_trade', 0.02)
        self.trailing_stop_pct = self.params.get('trailing_stop_pct', 0.03)
        
        # 做空开关
        self.enable_short = self.params.get('enable_short', True)
        
        # 市场状态跟踪
        self.market_state = "NEUTRAL"  # BULL, BEAR, NEUTRAL
        self.trend_strength = 0.0
        
        self.logger.info(f"TrendFollowingStrategy initialized with parameters:")
        self.logger.info(f"  EMA: {self.ema_fast}/{self.ema_medium}/{self.ema_slow}")
        self.logger.info(f"  ADX: {self.adx_period} (threshold: {self.adx_threshold})")
        self.logger.info(f"  Enable Short: {self.enable_short}")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        try:
            self.logger.debug("Calculating trend following indicators...")
            
            # 1. 多重EMA系统
            df['ema_fast'] = trend.ema(df['close'], self.ema_fast)
            df['ema_medium'] = trend.ema(df['close'], self.ema_medium)
            df['ema_slow'] = trend.ema(df['close'], self.ema_slow)
            
            # 2. ADX趋势强度
            df['adx'], df['di_plus'], df['di_minus'] = trend.adx(
                df['high'], df['low'], df['close'], self.adx_period
            )
            
            # 3. MACD动量指标
            df['macd'], df['macd_signal'], df['macd_histogram'] = trend.macd(
                df['close'], self.macd_fast, self.macd_slow, self.macd_signal
            )
            
            # 4. ATR波动率
            df['atr'] = volatility.atr(df['high'], df['low'], df['close'], self.atr_period)
            
            # 5. RSI过滤
            df['rsi'] = momentum.rsi(df['close'], self.rsi_period)
            
            # 6. 趋势强度指标
            df['trend_strength'] = self._calculate_trend_strength(df)
            
            # 7. 市场状态判断
            df['market_state'] = self._determine_market_state(df)
            
            # 8. 动态止损位
            df['dynamic_stop_long'] = self._calculate_dynamic_stop(df, 'LONG')
            df['dynamic_stop_short'] = self._calculate_dynamic_stop(df, 'SHORT')
            
            # 9. 支撑阻力位
            df['support'], df['resistance'] = composite.support_resistance(
                df['high'], df['low'], df['close'], window=20
            )
            
            self.logger.debug("Trend following indicators calculated successfully")
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            raise
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """计算综合趋势强度 (0-1)"""
        try:
            trend_scores = []
            
            for i in range(len(df)):
                if i < max(self.ema_slow, self.adx_period):
                    trend_scores.append(0.0)
                    continue
                
                score = 0.0
                
                # EMA排列得分 (40%)
                ema_fast = df['ema_fast'].iloc[i]
                ema_medium = df['ema_medium'].iloc[i]
                ema_slow = df['ema_slow'].iloc[i]
                
                if ema_fast > ema_medium > ema_slow:  # 多头排列
                    score += 0.4
                elif ema_fast < ema_medium < ema_slow:  # 空头排列
                    score += 0.4
                elif ema_fast > ema_medium or ema_medium > ema_slow:  # 部分排列
                    score += 0.2
                
                # ADX强度得分 (30%)
                adx = df['adx'].iloc[i]
                if adx > 50:
                    score += 0.3
                elif adx > self.adx_threshold:
                    score += 0.3 * (adx - self.adx_threshold) / (50 - self.adx_threshold)
                
                # MACD动量得分 (20%)
                macd = df['macd'].iloc[i]
                macd_signal = df['macd_signal'].iloc[i]
                if abs(macd - macd_signal) > 0:
                    score += 0.2 * min(abs(macd - macd_signal) / abs(macd_signal), 1.0)
                
                # 价格位置得分 (10%)
                close = df['close'].iloc[i]
                if close > ema_fast:
                    score += 0.1
                elif close < ema_fast:
                    score += 0.1
                
                trend_scores.append(min(score, 1.0))
            
            return pd.Series(trend_scores, index=df.index)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return pd.Series([0.0] * len(df), index=df.index)
    
    def _determine_market_state(self, df: pd.DataFrame) -> pd.Series:
        """判断市场状态"""
        try:
            states = []
            
            for i in range(len(df)):
                if i < max(self.ema_slow, self.adx_period):
                    states.append("NEUTRAL")
                    continue
                
                ema_fast = df['ema_fast'].iloc[i]
                ema_medium = df['ema_medium'].iloc[i]
                ema_slow = df['ema_slow'].iloc[i]
                adx = df['adx'].iloc[i]
                di_plus = df['di_plus'].iloc[i]
                di_minus = df['di_minus'].iloc[i]
                
                # 强趋势判断
                if adx > self.adx_threshold:
                    if (ema_fast > ema_medium > ema_slow and 
                        di_plus > di_minus):
                        states.append("BULL")
                    elif (ema_fast < ema_medium < ema_slow and 
                          di_minus > di_plus):
                        states.append("BEAR")
                    else:
                        states.append("NEUTRAL")
                else:
                    states.append("NEUTRAL")
            
            return pd.Series(states, index=df.index)
            
        except Exception as e:
            self.logger.error(f"Error determining market state: {e}")
            return pd.Series(["NEUTRAL"] * len(df), index=df.index)
    
    def _calculate_dynamic_stop(self, df: pd.DataFrame, direction: str) -> pd.Series:
        """计算动态止损位"""
        try:
            stops = []
            
            for i in range(len(df)):
                if i < self.atr_period:
                    stops.append(np.nan)
                    continue
                
                close = df['close'].iloc[i]
                atr = df['atr'].iloc[i]
                
                if direction == 'LONG':
                    # 多头止损：价格 - ATR * 倍数
                    stop = close - (atr * self.atr_multiplier)
                else:
                    # 空头止损：价格 + ATR * 倍数
                    stop = close + (atr * self.atr_multiplier)
                
                stops.append(stop)
            
            return pd.Series(stops, index=df.index)
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic stop: {e}")
            return pd.Series([np.nan] * len(df), index=df.index)
    
    def generate_signals(self, df: pd.DataFrame) -> List[str]:
        """生成交易信号"""
        try:
            self.logger.debug("Generating trend following signals...")
            
            signals = []
            
            for i in range(len(df)):
                if i < max(self.ema_slow, self.adx_period):
                    signals.append('HOLD')
                    continue
                
                # 获取当前指标值
                close = df['close'].iloc[i]
                ema_fast = df['ema_fast'].iloc[i]
                ema_medium = df['ema_medium'].iloc[i]
                ema_slow = df['ema_slow'].iloc[i]
                
                adx = df['adx'].iloc[i]
                di_plus = df['di_plus'].iloc[i]
                di_minus = df['di_minus'].iloc[i]
                
                macd = df['macd'].iloc[i]
                macd_signal = df['macd_signal'].iloc[i]
                macd_histogram = df['macd_histogram'].iloc[i]
                
                rsi = df['rsi'].iloc[i]
                trend_strength = df['trend_strength'].iloc[i]
                market_state = df['market_state'].iloc[i]
                
                # 信号生成逻辑
                signal = self._generate_signal_logic(
                    close, ema_fast, ema_medium, ema_slow,
                    adx, di_plus, di_minus,
                    macd, macd_signal, macd_histogram,
                    rsi, trend_strength, market_state
                )
                
                signals.append(signal)
            
            # 统计信号分布
            signal_counts = pd.Series(signals).value_counts()
            self.logger.info(f"Signal distribution: {dict(signal_counts)}")
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return ['HOLD'] * len(df)
    
    def _generate_signal_logic(self, close, ema_fast, ema_medium, ema_slow,
                              adx, di_plus, di_minus,
                              macd, macd_signal, macd_histogram,
                              rsi, trend_strength, market_state) -> str:
        """核心信号生成逻辑"""
        
        # 1. 趋势强度过滤
        if trend_strength < self.trend_strength_threshold:
            return 'HOLD'
        
        # 2. ADX强度过滤
        if adx < self.adx_threshold:
            return 'HOLD'
        
        # 3. 多头信号条件
        long_conditions = [
            # EMA多头排列
            ema_fast > ema_medium > ema_slow,
            # 价格在EMA快线上方
            close > ema_fast,
            # ADX显示上涨趋势
            di_plus > di_minus,
            # MACD金叉或在零轴上方
            macd > macd_signal or macd > 0,
            # RSI不超买
            rsi < self.rsi_overbought,
            # 市场状态为牛市
            market_state == "BULL"
        ]
        
        # 4. 空头信号条件
        short_conditions = [
            # EMA空头排列
            ema_fast < ema_medium < ema_slow,
            # 价格在EMA快线下方
            close < ema_fast,
            # ADX显示下跌趋势
            di_minus > di_plus,
            # MACD死叉或在零轴下方
            macd < macd_signal or macd < 0,
            # RSI不超卖
            rsi > self.rsi_oversold,
            # 市场状态为熊市
            market_state == "BEAR",
            # 允许做空
            self.enable_short
        ]
        
        # 5. 信号强度评估
        long_score = sum(long_conditions) / len(long_conditions)
        short_score = sum(short_conditions) / len(short_conditions)
        
        # 6. 信号决策
        if long_score >= 0.7:  # 70%条件满足
            return 'BUY'
        elif short_score >= 0.7 and self.enable_short:
            return 'SELL'
        else:
            return 'HOLD'
    
    def calculate_position_size(self, capital: float, current_price: float, 
                               atr: float) -> float:
        """基于ATR计算仓位大小"""
        try:
            # 风险金额
            risk_amount = capital * self.max_risk_per_trade
            
            # 止损距离
            stop_distance = atr * self.atr_multiplier
            
            # 仓位大小 = 风险金额 / 止损距离
            position_size = risk_amount / stop_distance
            
            # 限制最大仓位
            max_position = capital * 0.3  # 最大30%资金
            position_value = position_size * current_price
            
            if position_value > max_position:
                position_size = max_position / current_price
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return capital * 0.01 / current_price  # 默认1%风险
    
    def get_stop_loss_price(self, entry_price: float, direction: str, atr: float) -> float:
        """获取止损价格"""
        if direction.upper() == 'LONG':
            return entry_price - (atr * self.atr_multiplier)
        else:
            return entry_price + (atr * self.atr_multiplier)
    
    def get_take_profit_price(self, entry_price: float, direction: str, atr: float) -> float:
        """获取止盈价格"""
        profit_multiplier = self.atr_multiplier * 2  # 2:1盈亏比
        
        if direction.upper() == 'LONG':
            return entry_price + (atr * profit_multiplier)
        else:
            return entry_price - (atr * profit_multiplier)
    
    def update_trailing_stop(self, current_price: float, entry_price: float, 
                           direction: str, current_stop: float) -> float:
        """更新追踪止损"""
        try:
            if direction.upper() == 'LONG':
                # 多头追踪止损
                trailing_distance = current_price * self.trailing_stop_pct
                new_stop = current_price - trailing_distance
                return max(new_stop, current_stop)  # 只能向上调整
            else:
                # 空头追踪止损
                trailing_distance = current_price * self.trailing_stop_pct
                new_stop = current_price + trailing_distance
                return min(new_stop, current_stop)  # 只能向下调整
                
        except Exception as e:
            self.logger.error(f"Error updating trailing stop: {e}")
            return current_stop
    
    def get_strategy_info(self) -> Dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'type': 'Trend Following',
            'timeframes': ['5m', '15m', '30m', '1h', '4h'],
            'parameters': {
                'ema_fast': self.ema_fast,
                'ema_medium': self.ema_medium,
                'ema_slow': self.ema_slow,
                'adx_period': self.adx_period,
                'adx_threshold': self.adx_threshold,
                'atr_multiplier': self.atr_multiplier,
                'trend_strength_threshold': self.trend_strength_threshold,
                'enable_short': self.enable_short
            },
            'risk_management': {
                'max_risk_per_trade': self.max_risk_per_trade,
                'trailing_stop_pct': self.trailing_stop_pct,
                'stop_loss_method': 'ATR-based',
                'position_sizing': 'Risk-based'
            },
            'description': 'Professional trend following strategy with multi-timeframe analysis'
        }
    
    def get_default_params(self) -> Dict:
        """获取默认参数"""
        return DEFAULT_TREND_CONFIG


# 策略工厂函数
def create_trend_following_strategy(config: Dict) -> TrendFollowingStrategy:
    """创建趋势跟踪策略实例"""
    return TrendFollowingStrategy(config)


# 默认配置
DEFAULT_TREND_CONFIG = {
    # 核心EMA参数
    'ema_fast': 8,
    'ema_medium': 21,
    'ema_slow': 55,
    
    # 趋势强度参数
    'adx_period': 14,
    'adx_threshold': 25,
    
    # 动量参数
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    
    # 波动率参数
    'atr_period': 14,
    'atr_multiplier': 2.0,
    
    # 过滤参数
    'rsi_period': 14,
    'rsi_overbought': 80,
    'rsi_oversold': 20,
    
    # 信号参数
    'trend_strength_threshold': 0.6,
    
    # 风险管理
    'max_risk_per_trade': 0.02,
    'trailing_stop_pct': 0.03,
    
    # 交易方向
    'enable_short': True
}


# 不同市场的优化参数
MARKET_SPECIFIC_CONFIGS = {
    'BTC/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 8,
        'ema_medium': 21,
        'ema_slow': 55,
        'adx_threshold': 25,
        'atr_multiplier': 2.0,
        'trend_strength_threshold': 0.65
    },
    
    'ETH/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 10,
        'ema_medium': 21,
        'ema_slow': 50,
        'adx_threshold': 23,
        'atr_multiplier': 2.2,
        'trend_strength_threshold': 0.6
    },
    
    'BNB/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 12,
        'ema_medium': 26,
        'ema_slow': 50,
        'adx_threshold': 22,
        'atr_multiplier': 2.5,
        'trend_strength_threshold': 0.55
    },
    
    'SOL/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 8,
        'ema_medium': 21,
        'ema_slow': 55,
        'adx_threshold': 28,
        'atr_multiplier': 2.8,
        'trend_strength_threshold': 0.7
    },
    
    'PEPE/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 5,
        'ema_medium': 15,
        'ema_slow': 35,
        'adx_threshold': 30,
        'atr_multiplier': 3.0,
        'trend_strength_threshold': 0.75,
        'max_risk_per_trade': 0.015  # 降低风险
    },
    
    'DOGE/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 10,
        'ema_medium': 25,
        'ema_slow': 50,
        'adx_threshold': 20,
        'atr_multiplier': 2.5,
        'trend_strength_threshold': 0.55
    },
    
    'WLD/USDT': {
        **DEFAULT_TREND_CONFIG,
        'ema_fast': 12,
        'ema_medium': 26,
        'ema_slow': 55,
        'adx_threshold': 25,
        'atr_multiplier': 3.0,
        'trend_strength_threshold': 0.65,
        'max_risk_per_trade': 0.015  # 新币种降低风险
    }
}


if __name__ == "__main__":
    # 测试策略
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=1000, freq='1H')
    np.random.seed(42)
    
    # 生成趋势性数据
    trend = np.cumsum(np.random.normal(0.001, 0.02, 1000))
    prices = 45000 * np.exp(trend)
    
    test_df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.normal(0, 0.001, 1000)),
        'high': prices * (1 + np.random.uniform(0, 0.02, 1000)),
        'low': prices * (1 - np.random.uniform(0, 0.02, 1000)),
        'close': prices,
        'volume': np.random.uniform(100, 1000, 1000)
    })
    
    # 测试策略
    config = DEFAULT_TREND_CONFIG
    strategy = TrendFollowingStrategy(config)
    
    print("🧪 Testing Trend Following Strategy...")
    test_df = strategy.calculate_indicators(test_df)
    signals = strategy.generate_signals(test_df)
    
    print(f"✅ Strategy test completed")
    print(f"📊 Signals generated: {len(signals)}")
    print(f"📈 Signal distribution: {pd.Series(signals).value_counts().to_dict()}")
    print(f"🎯 Strategy info: {strategy.get_strategy_info()}")
