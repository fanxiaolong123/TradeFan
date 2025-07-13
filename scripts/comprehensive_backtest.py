#!/usr/bin/env python3
"""
全面回测脚本 - 支持多币种多时间框架
包含BTC、ETH、BNB、SOL、DOGE、PEPE、AAVE
支持5m、15m、30m、1h、4h、1d时间框架
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# 导入模块
from modules.enhanced_data_module import EnhancedDataModule

class ComprehensiveBacktester:
    """全面回测器 - 支持多币种多时间框架"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        
        # 扩展的回测配置
        self.config = {
            'symbols': [
                'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',  # 主流币种
                'DOGE/USDT', 'PEPE/USDT', 'AAVE/USDT'  # 新增币种
            ],
            'timeframes': [
                '5m', '15m', '30m',  # 短线时间框架
                '1h', '4h', '1d'     # 中长线时间框架
            ],
            'initial_capital': 10000,
            'position_size': 0.1,  # 10%仓位
            'max_positions': 3
        }
        
        # 时间框架配置
        self.timeframe_config = {
            '5m': {'test_days': 7, 'max_hold_hours': 2},     # 5分钟：测试7天，最多持有2小时
            '15m': {'test_days': 14, 'max_hold_hours': 6},   # 15分钟：测试14天，最多持有6小时
            '30m': {'test_days': 30, 'max_hold_hours': 12},  # 30分钟：测试30天，最多持有12小时
            '1h': {'test_days': 60, 'max_hold_hours': 24},   # 1小时：测试60天，最多持有24小时
            '4h': {'test_days': 180, 'max_hold_hours': 96},  # 4小时：测试180天，最多持有96小时
            '1d': {'test_days': 365, 'max_hold_hours': 240}  # 日线：测试365天，最多持有240小时
        }
        
        # 结果存储
        self.all_results = []
        self.summary_stats = {}
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        try:
            # EMA指标
            df['ema_8'] = df['close'].ewm(span=8, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema_55'] = df['close'].ewm(span=55, adjust=False).mean()
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
            bb_std = df['close'].rolling(20, min_periods=1).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # ATR (用于止损)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14, min_periods=1).mean()
            
            # 成交量指标
            df['volume_ma'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
        except Exception as e:
            print(f"   ⚠️  指标计算警告: {str(e)}")
        
        return df
    
    def generate_signal(self, data: pd.DataFrame, timeframe: str) -> int:
        """生成交易信号 - 根据时间框架调整策略"""
        if len(data) < 2:
            return 0
        
        current = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 检查数据有效性
        required_fields = ['ema_8', 'ema_21', 'ema_55', 'rsi', 'macd', 'macd_signal', 'bb_middle']
        if any(pd.isna(current[field]) for field in required_fields):
            return 0
        
        # 根据时间框架调整信号强度要求
        if timeframe in ['5m', '15m']:
            # 短线策略：更敏感的信号
            min_conditions = 3
        elif timeframe in ['30m', '1h']:
            # 中线策略：平衡的信号
            min_conditions = 4
        else:
            # 长线策略：更严格的信号
            min_conditions = 5
        
        # 多头信号条件
        long_conditions = [
            current['ema_8'] > current['ema_21'],  # 短期趋势向上
            current['ema_21'] > current['ema_55'],  # 中期趋势向上
            current['close'] > current['bb_middle'],  # 价格在布林带中轨上方
            current['rsi'] > 30 and current['rsi'] < 70,  # RSI在合理区间
            current['macd'] > current['macd_signal'],  # MACD金叉
            current['close'] > prev['close'],  # 价格上涨
            current['volume_ratio'] > 1.2 if 'volume_ratio' in current else True  # 成交量放大
        ]
        
        # 空头信号条件
        short_conditions = [
            current['ema_8'] < current['ema_21'],  # 短期趋势向下
            current['ema_21'] < current['ema_55'],  # 中期趋势向下
            current['close'] < current['bb_middle'],  # 价格在布林带中轨下方
            current['rsi'] > 30 and current['rsi'] < 70,  # RSI在合理区间
            current['macd'] < current['macd_signal'],  # MACD死叉
            current['close'] < prev['close'],  # 价格下跌
            current['volume_ratio'] > 1.2 if 'volume_ratio' in current else True  # 成交量放大
        ]
        
        # 信号强度计算
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        if long_score >= min_conditions:
            return 1  # 多头信号
        elif short_score >= min_conditions:
            return -1  # 空头信号
        else:
            return 0  # 无信号
    
    def execute_backtest(self, symbol: str, timeframe: str) -> dict:
        """执行单个配置的回测"""
        try:
            # 获取测试期间
            test_days = self.timeframe_config[timeframe]['test_days']
            end_date = datetime.now()
            start_date = end_date - timedelta(days=test_days)
            
            # 获取历史数据
            data = self.data_module.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if data.empty or len(data) < 100:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'insufficient_data',
                    'data_count': len(data) if not data.empty else 0
                }
            
            # 计算技术指标
            data = self.calculate_indicators(data)
            
            # 执行回测逻辑
            results = self._run_backtest_logic(data, symbol, timeframe)
            
            return results
            
        except Exception as e:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'error',
                'error': str(e)
            }
    
    def _run_backtest_logic(self, data: pd.DataFrame, symbol: str, timeframe: str) -> dict:
        """执行回测逻辑"""
        # 初始化变量
        capital = self.config['initial_capital']
        position = 0  # 0: 无仓位, 1: 多头, -1: 空头
        entry_price = 0
        entry_time = None
        stop_loss = 0
        take_profit = 0
        
        trades = []
        equity = [capital]
        max_hold_hours = self.timeframe_config[timeframe]['max_hold_hours']
        
        # 遍历数据
        start_idx = max(55, len(data) // 4)  # 从1/4处开始，确保指标稳定
        
        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            current_time = current['datetime']
            current_price = current['close']
            
            # 生成交易信号
            signal_data = data.iloc[max(0, i-10):i+1]
            signal = self.generate_signal(signal_data, timeframe)
            
            # 处理开仓信号
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = current_time
                
                # 设置止损止盈
                atr_value = current.get('atr', current_price * 0.02)  # 默认2%
                if signal == 1:  # 多头
                    stop_loss = entry_price - (atr_value * 2)
                    take_profit = entry_price + (atr_value * 4)  # 2:1盈亏比
                else:  # 空头
                    stop_loss = entry_price + (atr_value * 2)
                    take_profit = entry_price - (atr_value * 4)
            
            # 处理平仓条件
            elif position != 0:
                should_close = False
                close_reason = ""
                
                # 止损止盈检查
                if position == 1:  # 多头
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = "止损"
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = "止盈"
                else:  # 空头
                    if current_price >= stop_loss:
                        should_close = True
                        close_reason = "止损"
                    elif current_price <= take_profit:
                        should_close = True
                        close_reason = "止盈"
                
                # 反向信号
                if signal != 0 and signal != position:
                    should_close = True
                    close_reason = "反向信号"
                
                # 最大持仓时间
                if entry_time and (current_time - entry_time).total_seconds() / 3600 > max_hold_hours:
                    should_close = True
                    close_reason = "超时"
                
                # 执行平仓
                if should_close:
                    # 计算盈亏
                    if position == 1:
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    pnl_amount = capital * self.config['position_size'] * pnl_pct
                    capital += pnl_amount
                    
                    # 记录交易
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position': position,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'reason': close_reason,
                        'duration_hours': (current_time - entry_time).total_seconds() / 3600
                    }
                    trades.append(trade)
                    
                    # 重置仓位
                    position = 0
                    entry_price = 0
                    entry_time = None
            
            # 更新权益曲线
            if position != 0 and entry_price > 0:
                # 计算浮盈浮亏
                if position == 1:
                    unrealized_pnl = capital * self.config['position_size'] * ((current_price - entry_price) / entry_price)
                else:
                    unrealized_pnl = capital * self.config['position_size'] * ((entry_price - current_price) / entry_price)
                equity.append(capital + unrealized_pnl)
            else:
                equity.append(capital)
        
        # 计算回测结果
        results = self._calculate_performance(trades, equity, symbol, timeframe, len(data))
        
        return results
