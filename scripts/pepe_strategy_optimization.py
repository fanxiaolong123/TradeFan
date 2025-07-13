#!/usr/bin/env python3
"""
PEPE/USDT 各时间维度深度策略优化
基于回测结果，PEPE/USDT在4h和1d表现最佳，需要深度优化
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import itertools
from modules.enhanced_data_module import EnhancedDataModule

class PEPEStrategyOptimizer:
    """PEPE/USDT策略优化器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        self.symbol = 'PEPE/USDT'
        
        # 基于回测结果的时间框架优先级
        self.timeframes = {
            '4h': {'priority': 1, 'best_return': 7.23, 'win_rate': 38.9},  # 最佳表现
            '1d': {'priority': 2, 'best_return': 4.19, 'win_rate': 43.4},  # 次佳表现
            '30m': {'priority': 3, 'best_return': 0.07, 'win_rate': 30.8}, # 需要优化
            '5m': {'priority': 4, 'best_return': -0.15, 'win_rate': 31.1}  # 需要大幅优化
        }
        
        # 优化参数网格 - 针对PEPE的特性调整
        self.param_grids = {
            '4h': {  # 4小时策略 - 重点优化
                'ema_fast': [6, 8, 10, 12],
                'ema_medium': [18, 21, 24, 27],
                'ema_slow': [45, 55, 65],
                'rsi_lower': [25, 30, 35],
                'rsi_upper': [65, 70, 75],
                'bb_std': [1.8, 2.0, 2.2],
                'stop_loss': [0.015, 0.02, 0.025],  # 1.5%-2.5%
                'take_profit': [0.03, 0.04, 0.05],  # 3%-5%
                'volume_threshold': [1.2, 1.5, 2.0]
            },
            '1d': {  # 日线策略 - 稳定优化
                'ema_fast': [8, 10, 12],
                'ema_medium': [21, 24, 27],
                'ema_slow': [50, 55, 60],
                'rsi_lower': [30, 35],
                'rsi_upper': [65, 70],
                'bb_std': [2.0, 2.2],
                'stop_loss': [0.02, 0.025, 0.03],
                'take_profit': [0.04, 0.05, 0.06],
                'volume_threshold': [1.5, 2.0]
            },
            '30m': {  # 30分钟策略 - 激进优化
                'ema_fast': [5, 6, 8],
                'ema_medium': [15, 18, 21],
                'ema_slow': [40, 45, 50],
                'rsi_lower': [20, 25, 30],
                'rsi_upper': [70, 75, 80],
                'bb_std': [1.5, 1.8, 2.0],
                'stop_loss': [0.01, 0.015, 0.02],
                'take_profit': [0.025, 0.03, 0.035],
                'volume_threshold': [1.5, 2.0, 2.5]
            },
            '5m': {  # 5分钟策略 - 超短线优化
                'ema_fast': [3, 5, 6],
                'ema_medium': [12, 15, 18],
                'ema_slow': [30, 35, 40],
                'rsi_lower': [20, 25],
                'rsi_upper': [75, 80],
                'bb_std': [1.5, 1.8],
                'stop_loss': [0.008, 0.01, 0.012],
                'take_profit': [0.015, 0.02, 0.025],
                'volume_threshold': [2.0, 2.5, 3.0]
            }
        }
    
    def calculate_advanced_indicators(self, data: pd.DataFrame, params: dict) -> pd.DataFrame:
        """计算高级技术指标"""
        df = data.copy()
        
        try:
            # EMA指标
            df['ema_fast'] = df['close'].ewm(span=params['ema_fast'], adjust=False).mean()
            df['ema_medium'] = df['close'].ewm(span=params['ema_medium'], adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=params['ema_slow'], adjust=False).mean()
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
            bb_std = df['close'].rolling(20, min_periods=1).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * params['bb_std'])
            df['bb_lower'] = df['bb_middle'] - (bb_std * params['bb_std'])
            
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
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14, min_periods=1).mean()
            
            # 成交量指标
            df['volume_ma'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # PEPE特有指标 - 波动率和动量
            df['volatility'] = df['close'].rolling(10).std() / df['close'].rolling(10).mean()
            df['momentum'] = df['close'] / df['close'].shift(5) - 1
            
            # 价格位置指标
            df['price_position'] = (df['close'] - df['close'].rolling(20).min()) / (df['close'].rolling(20).max() - df['close'].rolling(20).min())
            
        except Exception as e:
            print(f"   ⚠️  指标计算警告: {str(e)}")
        
        return df
    
    def generate_pepe_signal(self, data: pd.DataFrame, params: dict, timeframe: str) -> int:
        """生成PEPE专用交易信号"""
        if len(data) < 2:
            return 0
        
        current = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 检查数据有效性
        required_fields = ['ema_fast', 'ema_medium', 'ema_slow', 'rsi', 'macd', 'macd_signal', 'bb_middle', 'volume_ratio']
        if any(pd.isna(current[field]) for field in required_fields):
            return 0
        
        # PEPE特有的信号条件
        # 多头信号条件
        long_conditions = [
            current['ema_fast'] > current['ema_medium'],  # 短期趋势向上
            current['ema_medium'] > current['ema_slow'],  # 中期趋势向上
            current['close'] > current['bb_middle'],  # 价格在布林带中轨上方
            current['rsi'] > params['rsi_lower'] and current['rsi'] < params['rsi_upper'],  # RSI在合理区间
            current['macd'] > current['macd_signal'],  # MACD金叉
            current['close'] > prev['close'],  # 价格上涨
            current['volume_ratio'] > params['volume_threshold'],  # 成交量放大
            current.get('momentum', 0) > 0.01,  # 动量向上
            current.get('price_position', 0.5) > 0.3,  # 价格位置不在底部
        ]
        
        # 空头信号条件 (PEPE更适合做多)
        short_conditions = [
            current['ema_fast'] < current['ema_medium'],  # 短期趋势向下
            current['ema_medium'] < current['ema_slow'],  # 中期趋势向下
            current['close'] < current['bb_lower'],  # 价格跌破布林带下轨
            current['rsi'] < 30,  # RSI超卖
            current['macd'] < current['macd_signal'],  # MACD死叉
            current['close'] < prev['close'],  # 价格下跌
            current['volume_ratio'] > params['volume_threshold'],  # 成交量放大
            current.get('momentum', 0) < -0.02,  # 动量向下
        ]
        
        # 根据时间框架调整信号强度要求
        if timeframe == '5m':
            min_long_conditions = 5  # 超短线，更敏感
            min_short_conditions = 4
        elif timeframe == '30m':
            min_long_conditions = 6  # 短线，平衡
            min_short_conditions = 5
        elif timeframe == '4h':
            min_long_conditions = 7  # 中线，更严格
            min_short_conditions = 6
        else:  # 1d
            min_long_conditions = 7  # 长线，最严格
            min_short_conditions = 6
        
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        if long_score >= min_long_conditions:
            return 1  # 多头信号
        elif short_score >= min_short_conditions and timeframe in ['5m', '30m']:  # 只在短时间框架做空
            return -1  # 空头信号
        else:
            return 0  # 无信号
    
    def backtest_strategy(self, data: pd.DataFrame, params: dict, timeframe: str) -> dict:
        """回测策略"""
        if len(data) < 100:
            return {'total_return': -999, 'win_rate': 0, 'total_trades': 0}
        
        # 计算指标
        data = self.calculate_advanced_indicators(data, params)
        
        # 初始化变量
        capital = 10000
        position = 0
        entry_price = 0
        entry_time = None
        
        trades = []
        equity = [capital]
        
        # 时间框架配置
        max_hold_hours = {'5m': 1, '30m': 6, '4h': 48, '1d': 120}[timeframe]
        
        # 遍历数据
        start_idx = max(50, len(data) // 4)
        
        for i in range(start_idx, len(data)):
            current = data.iloc[i]
            current_time = current['datetime']
            current_price = current['close']
            
            # 生成交易信号
            signal_data = data.iloc[max(0, i-10):i+1]
            signal = self.generate_pepe_signal(signal_data, params, timeframe)
            
            # 处理开仓信号
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = current_time
            
            # 处理平仓条件
            elif position != 0:
                should_close = False
                close_reason = ""
                
                # 止损止盈
                if position == 1:  # 多头
                    if current_price <= entry_price * (1 - params['stop_loss']):
                        should_close = True
                        close_reason = "止损"
                    elif current_price >= entry_price * (1 + params['take_profit']):
                        should_close = True
                        close_reason = "止盈"
                else:  # 空头
                    if current_price >= entry_price * (1 + params['stop_loss']):
                        should_close = True
                        close_reason = "止损"
                    elif current_price <= entry_price * (1 - params['take_profit']):
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
                    if position == 1:
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    pnl_amount = capital * 0.1 * pnl_pct  # 10%仓位
                    capital += pnl_amount
                    
                    trades.append({
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'reason': close_reason,
                        'duration_hours': (current_time - entry_time).total_seconds() / 3600
                    })
                    
                    position = 0
                    entry_price = 0
                    entry_time = None
            
            # 更新权益曲线
            if position != 0 and entry_price > 0:
                if position == 1:
                    unrealized_pnl = capital * 0.1 * ((current_price - entry_price) / entry_price)
                else:
                    unrealized_pnl = capital * 0.1 * ((entry_price - current_price) / entry_price)
                equity.append(capital + unrealized_pnl)
            else:
                equity.append(capital)
        
        # 计算结果
        if not trades:
            return {'total_return': -999, 'win_rate': 0, 'total_trades': 0, 'max_drawdown': 0}
        
        total_return = (capital - 10000) / 10000 * 100
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        win_rate = len(winning_trades) / len(trades) * 100
        
        # 最大回撤
        peak = 10000
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'max_drawdown': max_dd,
            'avg_duration': np.mean([t['duration_hours'] for t in trades]),
            'profit_factor': abs(np.mean([t['pnl_amount'] for t in winning_trades]) / 
                               np.mean([t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0])) if len([t for t in trades if t['pnl_amount'] <= 0]) > 0 else 0
        }
    
    def optimize_timeframe(self, timeframe: str, max_combinations: int = 200):
        """优化特定时间框架"""
        print(f"\n🎯 优化 PEPE/USDT {timeframe} 策略...")
        
        # 获取数据
        data = self.data_module.get_historical_data(self.symbol, timeframe)
        
        if data.empty or len(data) < 100:
            print(f"❌ {timeframe} 数据不足: {len(data)} 条")
            return None
        
        print(f"📊 使用 {len(data)} 条数据进行优化")
        
        # 生成参数组合
        param_grid = self.param_grids[timeframe]
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        # 限制组合数量
        all_combinations = list(itertools.product(*param_values))
        if len(all_combinations) > max_combinations:
            # 随机采样
            import random
            random.seed(42)
            combinations = random.sample(all_combinations, max_combinations)
        else:
            combinations = all_combinations
        
        print(f"🔍 测试 {len(combinations)} 个参数组合...")
        
        best_result = {'total_return': -999}
        best_params = None
        
        for i, combination in enumerate(combinations):
            params = dict(zip(param_names, combination))
            
            # 跳过不合理的参数组合
            if params['ema_fast'] >= params['ema_medium'] or params['ema_medium'] >= params['ema_slow']:
                continue
            if params['stop_loss'] >= params['take_profit']:
                continue
            
            result = self.backtest_strategy(data, params, timeframe)
            
            if result['total_return'] > best_result['total_return']:
                best_result = result
                best_params = params
            
            if (i + 1) % 50 == 0:
                print(f"   进度: {i+1}/{len(combinations)} ({(i+1)/len(combinations)*100:.1f}%)")
        
        return {
            'timeframe': timeframe,
            'best_params': best_params,
            'best_result': best_result,
            'original_performance': self.timeframes[timeframe]
        }
    
    def run_comprehensive_optimization(self):
        """运行全面优化"""
        print("🚀 PEPE/USDT 全面策略优化")
        print("=" * 60)
        
        results = {}
        
        # 按优先级优化各时间框架
        for timeframe in sorted(self.timeframes.keys(), key=lambda x: self.timeframes[x]['priority']):
            result = self.optimize_timeframe(timeframe)
            if result:
                results[timeframe] = result
        
        # 生成优化报告
        self.generate_optimization_report(results)
        
        return results
    
    def generate_optimization_report(self, results: dict):
        """生成优化报告"""
        print("\n" + "=" * 60)
        print("📊 PEPE/USDT 策略优化报告")
        print("=" * 60)
        
        for timeframe, result in results.items():
            if not result:
                continue
                
            original = result['original_performance']
            optimized = result['best_result']
            params = result['best_params']
            
            print(f"\n🎯 {timeframe} 时间框架优化结果:")
            print(f"   原始表现: {original['best_return']:.2f}% (胜率 {original['win_rate']:.1f}%)")
            print(f"   优化后表现: {optimized['total_return']:.2f}% (胜率 {optimized['win_rate']:.1f}%)")
            print(f"   改善幅度: {optimized['total_return'] - original['best_return']:.2f}%")
            print(f"   交易次数: {optimized['total_trades']}")
            print(f"   最大回撤: {optimized['max_drawdown']:.2f}%")
            print(f"   盈亏比: {optimized['profit_factor']:.2f}")
            
            print(f"   最佳参数:")
            for param, value in params.items():
                print(f"     {param}: {value}")
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存详细结果
        optimization_data = []
        for timeframe, result in results.items():
            if result:
                row = {
                    'timeframe': timeframe,
                    'original_return': result['original_performance']['best_return'],
                    'optimized_return': result['best_result']['total_return'],
                    'improvement': result['best_result']['total_return'] - result['original_performance']['best_return'],
                    'win_rate': result['best_result']['win_rate'],
                    'total_trades': result['best_result']['total_trades'],
                    'max_drawdown': result['best_result']['max_drawdown'],
                    'profit_factor': result['best_result']['profit_factor']
                }
                
                # 添加最佳参数
                for param, value in result['best_params'].items():
                    row[f'param_{param}'] = value
                
                optimization_data.append(row)
        
        if optimization_data:
            os.makedirs('results', exist_ok=True)
            results_df = pd.DataFrame(optimization_data)
            results_file = f'results/pepe_optimization_{timestamp}.csv'
            results_df.to_csv(results_file, index=False)
            print(f"\n💾 优化结果已保存: {results_file}")


def main():
    """主函数"""
    print("🎯 PEPE/USDT 深度策略优化系统")
    print("基于回测结果进行针对性优化")
    print("=" * 60)
    
    optimizer = PEPEStrategyOptimizer()
    results = optimizer.run_comprehensive_optimization()
    
    print(f"\n🎉 PEPE/USDT 策略优化完成!")


if __name__ == "__main__":
    main()
