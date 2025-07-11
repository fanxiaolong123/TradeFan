"""
多时间框架分析模块
Multi-Timeframe Analysis Module

提供多个时间周期的综合分析，用于提高交易信号的准确性
支持5分钟到日线的多时间框架分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

@dataclass
class TimeframeAnalysis:
    """时间框架分析结果"""
    timeframe: str
    trend_direction: int  # 1: 上涨, -1: 下跌, 0: 横盘
    trend_strength: float  # 0-100
    support_level: float
    resistance_level: float
    key_levels: List[float]
    volume_profile: Dict[str, float]
    volatility: float
    momentum: float

class MultiTimeframeAnalyzer:
    """多时间框架分析器"""
    
    def __init__(self, timeframes: List[str] = None):
        """
        初始化多时间框架分析器
        
        Args:
            timeframes: 时间框架列表，如 ['5m', '15m', '30m', '1h', '4h', '1d']
        """
        self.timeframes = timeframes or ['5m', '15m', '30m', '1h', '4h', '1d']
        self.logger = logging.getLogger(__name__)
        
        # 时间框架权重 (用于综合分析)
        self.timeframe_weights = {
            '1m': 0.05,
            '5m': 0.10,
            '15m': 0.15,
            '30m': 0.20,
            '1h': 0.25,
            '4h': 0.15,
            '1d': 0.10
        }
        
        # 缓存分析结果
        self.analysis_cache = {}
        self.cache_expiry = {}
    
    def analyze_all_timeframes(self, symbol: str, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, TimeframeAnalysis]:
        """
        分析所有时间框架
        
        Args:
            symbol: 交易对符号
            data_dict: 各时间框架的数据字典 {'5m': df, '15m': df, ...}
            
        Returns:
            各时间框架的分析结果
        """
        results = {}
        
        for timeframe in self.timeframes:
            if timeframe in data_dict and not data_dict[timeframe].empty:
                try:
                    analysis = self._analyze_single_timeframe(
                        data_dict[timeframe], timeframe
                    )
                    results[timeframe] = analysis
                    
                    # 缓存结果
                    cache_key = f"{symbol}_{timeframe}"
                    self.analysis_cache[cache_key] = analysis
                    self.cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)
                    
                except Exception as e:
                    self.logger.error(f"分析时间框架 {timeframe} 失败: {e}")
                    continue
        
        return results
    
    def _analyze_single_timeframe(self, data: pd.DataFrame, timeframe: str) -> TimeframeAnalysis:
        """
        分析单个时间框架
        
        Args:
            data: OHLCV数据
            timeframe: 时间框架
            
        Returns:
            时间框架分析结果
        """
        # 计算技术指标
        df = self._calculate_indicators(data.copy())
        
        # 趋势分析
        trend_direction, trend_strength = self._analyze_trend(df)
        
        # 支撑阻力分析
        support_level, resistance_level = self._find_support_resistance(df)
        
        # 关键价位
        key_levels = self._find_key_levels(df)
        
        # 成交量分析
        volume_profile = self._analyze_volume_profile(df)
        
        # 波动率分析
        volatility = self._calculate_volatility(df)
        
        # 动量分析
        momentum = self._calculate_momentum(df)
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            support_level=support_level,
            resistance_level=resistance_level,
            key_levels=key_levels,
            volume_profile=volume_profile,
            volatility=volatility,
            momentum=momentum
        )
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # EMA
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_55'] = df['close'].ewm(span=55).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # SMA
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # 成交量指标
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def _analyze_trend(self, df: pd.DataFrame) -> Tuple[int, float]:
        """
        分析趋势方向和强度
        
        Returns:
            (趋势方向, 趋势强度)
        """
        if len(df) < 55:
            return 0, 0.0
        
        latest = df.iloc[-1]
        
        # EMA排列分析
        ema_score = 0
        if latest['ema_8'] > latest['ema_21'] > latest['ema_55']:
            ema_score = 1  # 多头排列
        elif latest['ema_8'] < latest['ema_21'] < latest['ema_55']:
            ema_score = -1  # 空头排列
        
        # 价格相对于EMA的位置
        price_above_emas = sum([
            latest['close'] > latest['ema_8'],
            latest['close'] > latest['ema_21'],
            latest['close'] > latest['ema_55']
        ])
        
        # MACD趋势
        macd_trend = 1 if latest['macd'] > latest['macd_signal'] else -1
        
        # RSI趋势
        rsi_trend = 1 if latest['rsi'] > 50 else -1
        
        # 综合趋势方向
        trend_signals = [ema_score, macd_trend, rsi_trend]
        if price_above_emas >= 2:
            trend_signals.append(1)
        elif price_above_emas <= 1:
            trend_signals.append(-1)
        
        trend_direction = 1 if sum(trend_signals) > 0 else (-1 if sum(trend_signals) < 0 else 0)
        
        # 趋势强度计算
        strength_factors = []
        
        # EMA斜率
        if len(df) >= 5:
            ema21_slope = (latest['ema_21'] - df['ema_21'].iloc[-5]) / df['ema_21'].iloc[-5]
            strength_factors.append(abs(ema21_slope) * 100)
        
        # 价格动量
        if len(df) >= 10:
            price_momentum = (latest['close'] - df['close'].iloc[-10]) / df['close'].iloc[-10]
            strength_factors.append(abs(price_momentum) * 100)
        
        # RSI偏离中线程度
        rsi_deviation = abs(latest['rsi'] - 50) / 50
        strength_factors.append(rsi_deviation * 100)
        
        # MACD强度
        if latest['macd_signal'] != 0:
            macd_strength = abs(latest['macd'] / latest['macd_signal'])
            strength_factors.append(min(macd_strength * 20, 100))
        
        trend_strength = np.mean(strength_factors) if strength_factors else 0
        trend_strength = min(max(trend_strength, 0), 100)
        
        return trend_direction, trend_strength
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Tuple[float, float]:
        """
        寻找支撑和阻力位
        
        Returns:
            (支撑位, 阻力位)
        """
        if len(df) < 50:
            return df['low'].min(), df['high'].max()
        
        # 使用最近50根K线
        recent_data = df.tail(50)
        
        # 寻找局部高点和低点
        highs = []
        lows = []
        
        for i in range(2, len(recent_data) - 2):
            # 局部高点
            if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                highs.append(recent_data['high'].iloc[i])
            
            # 局部低点
            if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                lows.append(recent_data['low'].iloc[i])
        
        # 计算支撑阻力位
        current_price = df['close'].iloc[-1]
        
        # 阻力位：高于当前价格的最近高点
        resistance_candidates = [h for h in highs if h > current_price]
        resistance_level = min(resistance_candidates) if resistance_candidates else df['high'].max()
        
        # 支撑位：低于当前价格的最近低点
        support_candidates = [l for l in lows if l < current_price]
        support_level = max(support_candidates) if support_candidates else df['low'].min()
        
        return support_level, resistance_level
    
    def _find_key_levels(self, df: pd.DataFrame) -> List[float]:
        """寻找关键价位"""
        key_levels = []
        
        # 整数关键位
        current_price = df['close'].iloc[-1]
        price_range = df['high'].max() - df['low'].min()
        
        # 根据价格范围确定整数位间隔
        if price_range > 1000:
            interval = 100
        elif price_range > 100:
            interval = 10
        elif price_range > 10:
            interval = 1
        else:
            interval = 0.1
        
        # 寻找附近的整数位
        base = int(current_price / interval) * interval
        for i in range(-3, 4):
            level = base + (i * interval)
            if df['low'].min() <= level <= df['high'].max():
                key_levels.append(level)
        
        # 添加重要的移动平均线
        if len(df) >= 200:
            key_levels.append(df['ema_200'].iloc[-1])
        if len(df) >= 55:
            key_levels.append(df['ema_55'].iloc[-1])
        
        # 添加布林带
        key_levels.extend([
            df['bb_upper'].iloc[-1],
            df['bb_middle'].iloc[-1],
            df['bb_lower'].iloc[-1]
        ])
        
        return sorted(list(set(key_levels)))
    
    def _analyze_volume_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """分析成交量分布"""
        recent_data = df.tail(50)
        
        return {
            'avg_volume': recent_data['volume'].mean(),
            'volume_trend': (recent_data['volume'].iloc[-10:].mean() / 
                           recent_data['volume'].iloc[-20:-10].mean() - 1) * 100,
            'volume_spike_ratio': recent_data['volume'].max() / recent_data['volume'].mean(),
            'high_volume_price': recent_data.loc[recent_data['volume'].idxmax(), 'close']
        }
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """计算波动率"""
        if len(df) < 20:
            return 0.0
        
        # 使用ATR作为波动率指标
        atr_ratio = df['atr'].iloc[-1] / df['close'].iloc[-1]
        return atr_ratio * 100
    
    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """计算动量"""
        if len(df) < 10:
            return 0.0
        
        # 10期价格动量
        price_momentum = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
        
        # RSI动量
        rsi_momentum = (df['rsi'].iloc[-1] - 50) / 50
        
        # MACD动量
        macd_momentum = df['macd_hist'].iloc[-1] / df['close'].iloc[-1] if df['close'].iloc[-1] != 0 else 0
        
        # 综合动量
        momentum = (price_momentum * 0.5 + rsi_momentum * 0.3 + macd_momentum * 0.2) * 100
        
        return momentum
    
    def get_trend_alignment(self, analyses: Dict[str, TimeframeAnalysis]) -> Dict[str, Any]:
        """
        获取多时间框架趋势一致性分析
        
        Args:
            analyses: 各时间框架分析结果
            
        Returns:
            趋势一致性分析结果
        """
        if not analyses:
            return {'alignment_score': 0, 'dominant_trend': 0, 'confidence': 0}
        
        # 计算加权趋势得分
        weighted_trend = 0
        total_weight = 0
        trend_directions = []
        
        for timeframe, analysis in analyses.items():
            weight = self.timeframe_weights.get(timeframe, 0.1)
            weighted_trend += analysis.trend_direction * analysis.trend_strength * weight
            total_weight += weight
            trend_directions.append(analysis.trend_direction)
        
        # 趋势一致性得分
        bullish_count = sum(1 for t in trend_directions if t > 0)
        bearish_count = sum(1 for t in trend_directions if t < 0)
        neutral_count = sum(1 for t in trend_directions if t == 0)
        
        total_count = len(trend_directions)
        alignment_score = max(bullish_count, bearish_count) / total_count * 100
        
        # 主导趋势
        if bullish_count > bearish_count and bullish_count > neutral_count:
            dominant_trend = 1
        elif bearish_count > bullish_count and bearish_count > neutral_count:
            dominant_trend = -1
        else:
            dominant_trend = 0
        
        # 信心度
        confidence = alignment_score * (abs(weighted_trend) / total_weight if total_weight > 0 else 0)
        
        return {
            'alignment_score': alignment_score,
            'dominant_trend': dominant_trend,
            'confidence': min(confidence, 100),
            'bullish_timeframes': bullish_count,
            'bearish_timeframes': bearish_count,
            'neutral_timeframes': neutral_count,
            'weighted_trend_score': weighted_trend / total_weight if total_weight > 0 else 0
        }
    
    def get_entry_confirmation(self, analyses: Dict[str, TimeframeAnalysis], 
                             signal_timeframe: str) -> Dict[str, Any]:
        """
        获取入场确认信号
        
        Args:
            analyses: 各时间框架分析结果
            signal_timeframe: 信号时间框架
            
        Returns:
            入场确认结果
        """
        if signal_timeframe not in analyses:
            return {'confirmed': False, 'reason': '信号时间框架数据不足'}
        
        signal_analysis = analyses[signal_timeframe]
        
        # 获取更高时间框架的趋势
        higher_timeframes = []
        timeframe_order = ['5m', '15m', '30m', '1h', '4h', '1d']
        
        try:
            signal_index = timeframe_order.index(signal_timeframe)
            higher_timeframes = timeframe_order[signal_index + 1:]
        except ValueError:
            pass
        
        # 检查高时间框架趋势一致性
        higher_trend_support = 0
        higher_trend_count = 0
        
        for tf in higher_timeframes:
            if tf in analyses:
                higher_analysis = analyses[tf]
                if (signal_analysis.trend_direction > 0 and higher_analysis.trend_direction > 0) or \
                   (signal_analysis.trend_direction < 0 and higher_analysis.trend_direction < 0):
                    higher_trend_support += 1
                higher_trend_count += 1
        
        # 确认条件
        confirmations = []
        
        # 1. 趋势强度足够
        if signal_analysis.trend_strength > 30:
            confirmations.append("趋势强度足够")
        
        # 2. 高时间框架支持
        if higher_trend_count > 0 and higher_trend_support / higher_trend_count >= 0.6:
            confirmations.append("高时间框架趋势支持")
        
        # 3. 关键位突破
        current_price = signal_analysis.support_level  # 这里需要实际的当前价格
        if signal_analysis.trend_direction > 0 and current_price > signal_analysis.resistance_level:
            confirmations.append("突破阻力位")
        elif signal_analysis.trend_direction < 0 and current_price < signal_analysis.support_level:
            confirmations.append("跌破支撑位")
        
        # 4. 动量确认
        if abs(signal_analysis.momentum) > 20:
            confirmations.append("动量强劲")
        
        # 5. 波动率适中
        if 10 < signal_analysis.volatility < 50:
            confirmations.append("波动率适中")
        
        confirmed = len(confirmations) >= 2
        
        return {
            'confirmed': confirmed,
            'confirmations': confirmations,
            'confirmation_count': len(confirmations),
            'higher_timeframe_support': higher_trend_support / higher_trend_count if higher_trend_count > 0 else 0,
            'signal_strength': signal_analysis.trend_strength,
            'risk_level': 'low' if len(confirmations) >= 4 else ('medium' if len(confirmations) >= 2 else 'high')
        }
    
    def clear_cache(self):
        """清理过期缓存"""
        current_time = datetime.now()
        expired_keys = [
            key for key, expiry_time in self.cache_expiry.items()
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            self.analysis_cache.pop(key, None)
            self.cache_expiry.pop(key, None)
    
    def get_market_structure(self, analyses: Dict[str, TimeframeAnalysis]) -> Dict[str, Any]:
        """
        获取市场结构分析
        
        Args:
            analyses: 各时间框架分析结果
            
        Returns:
            市场结构分析结果
        """
        if not analyses:
            return {}
        
        # 获取关键支撑阻力位
        all_support_levels = []
        all_resistance_levels = []
        
        for analysis in analyses.values():
            all_support_levels.append(analysis.support_level)
            all_resistance_levels.append(analysis.resistance_level)
        
        # 计算平均支撑阻力位
        avg_support = np.mean(all_support_levels)
        avg_resistance = np.mean(all_resistance_levels)
        
        # 市场结构状态
        structure_state = "consolidation"  # 默认盘整
        
        # 判断市场结构
        trend_alignment = self.get_trend_alignment(analyses)
        if trend_alignment['alignment_score'] > 70:
            if trend_alignment['dominant_trend'] > 0:
                structure_state = "uptrend"
            elif trend_alignment['dominant_trend'] < 0:
                structure_state = "downtrend"
        
        return {
            'structure_state': structure_state,
            'avg_support': avg_support,
            'avg_resistance': avg_resistance,
            'support_strength': len([s for s in all_support_levels if abs(s - avg_support) / avg_support < 0.02]),
            'resistance_strength': len([r for r in all_resistance_levels if abs(r - avg_resistance) / avg_resistance < 0.02]),
            'trend_alignment': trend_alignment
        }
