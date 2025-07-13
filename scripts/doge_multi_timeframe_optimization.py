#!/usr/bin/env python3
"""
DOGE/USDT 多时间框架策略深度优化
基于回测结果，DOGE/USDT在多个时间框架都表现良好，适合多时间框架策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import itertools
from modules.enhanced_data_module import EnhancedDataModule

class DOGEMultiTimeframeOptimizer:
    """DOGE/USDT多时间框架策略优化器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        self.symbol = 'DOGE/USDT'
        
        # 基于回测结果的时间框架表现
        self.timeframe_performance = {
            '1d': {'return': 4.06, 'win_rate': 45.5, 'trades': 44},   # 最佳
            '4h': {'return': 3.50, 'win_rate': 33.3, 'trades': 84},   # 次佳
            '1h': {'return': 2.88, 'win_rate': 33.7, 'trades': 86},   # 第三
            '30m': {'return': 2.42, 'win_rate': 31.6, 'trades': 76},  # 第四
            '5m': {'return': 1.16, 'win_rate': 36.8, 'trades': 87},   # 第五
            '15m': {'return': 0.72, 'win_rate': 31.5, 'trades': 73}   # 第六
        }
        
        # 多时间框架组合策略
        self.mtf_combinations = [
            {'primary': '1d', 'secondary': '4h', 'entry': '1h'},      # 长线主导
            {'primary': '4h', 'secondary': '1h', 'entry': '30m'},     # 中线主导
            {'primary': '1h', 'secondary': '30m', 'entry': '15m'},    # 短线主导
            {'primary': '4h', 'secondary': '1d', 'entry': '1h'},      # 平衡策略
        ]
        
        # 优化参数
        self.optimization_params = {
            'trend_confirmation_periods': [3, 5, 7, 10],  # 趋势确认周期
            'signal_strength_threshold': [0.6, 0.7, 0.8, 0.9],  # 信号强度阈值
            'volume_confirmation': [1.2, 1.5, 2.0, 2.5],  # 成交量确认倍数
            'rsi_divergence_periods': [5, 7, 10, 14],  # RSI背离检测周期
            'momentum_threshold': [0.01, 0.02, 0.03, 0.05],  # 动量阈值
            'volatility_filter': [0.02, 0.03, 0.05, 0.08],  # 波动率过滤
        }
    
    def get_multi_timeframe_data(self, timeframes: list) -> dict:
        """获取多时间框架数据"""
        data_dict = {}
        
        for tf in timeframes:
            data = self.data_module.get_historical_data(self.symbol, tf)
            if not data.empty and len(data) >= 100:
                data_dict[tf] = self.calculate_indicators(data, tf)
            else:
                print(f"⚠️  {tf} 数据不足")
        
        return data_dict
    
    def calculate_indicators(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        try:
            # 基础EMA指标
            df['ema_8'] = df['close'].ewm(span=8, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema_55'] = df['close'].ewm(span=55, adjust=False).mean()
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
            bb_std = df['close'].rolling(20, min_periods=1).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2.0)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2.0)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # RSI和RSI背离
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
            
            # ATR和波动率
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14, min_periods=1).mean()
            df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
            
            # 成交量指标
            df['volume_ma'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            df['volume_trend'] = df['volume_ma'] / df['volume_ma'].shift(5)
            
            # 动量指标
            df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
            
            # 趋势强度
            df['trend_strength'] = abs(df['ema_8'] - df['ema_21']) / df['ema_21']
            
            # 价格位置
            df['price_position'] = (df['close'] - df['close'].rolling(50).min()) / (df['close'].rolling(50).max() - df['close'].rolling(50).min())
            
            # DOGE特有指标 - 社交媒体影响模拟
            df['social_momentum'] = df['volume_ratio'] * df['momentum_5']  # 成交量动量组合
            df['meme_strength'] = df['volatility'] * df['volume_ratio']    # 波动率成交量组合
            
        except Exception as e:
            print(f"   ⚠️  {timeframe} 指标计算警告: {str(e)}")
        
        return df
    
    def analyze_timeframe_correlation(self, data_dict: dict) -> dict:
        """分析时间框架间的相关性"""
        correlations = {}
        
        # 获取共同时间点的数据
        common_dates = None
        for tf, data in data_dict.items():
            if common_dates is None:
                common_dates = set(data['datetime'].dt.date)
            else:
                common_dates = common_dates.intersection(set(data['datetime'].dt.date))
        
        if len(common_dates) < 50:
            return correlations
        
        # 计算相关性
        for tf1 in data_dict.keys():
            for tf2 in data_dict.keys():
                if tf1 != tf2:
                    # 简化相关性计算
                    data1 = data_dict[tf1]
                    data2 = data_dict[tf2]
                    
                    # 计算收益率相关性
                    returns1 = data1['close'].pct_change().dropna()
                    returns2 = data2['close'].pct_change().dropna()
                    
                    if len(returns1) > 20 and len(returns2) > 20:
                        # 取较短的长度
                        min_len = min(len(returns1), len(returns2))
                        corr = np.corrcoef(returns1.tail(min_len), returns2.tail(min_len))[0, 1]
                        correlations[f"{tf1}_{tf2}"] = corr
        
        return correlations
    
    def generate_mtf_signal(self, data_dict: dict, mtf_config: dict, params: dict, current_idx: dict) -> dict:
        """生成多时间框架信号"""
        signals = {}
        
        primary_tf = mtf_config['primary']
        secondary_tf = mtf_config['secondary']
        entry_tf = mtf_config['entry']
        
        # 检查数据可用性
        for tf in [primary_tf, secondary_tf, entry_tf]:
            if tf not in data_dict or current_idx[tf] >= len(data_dict[tf]):
                return {'signal': 0, 'strength': 0, 'reason': 'insufficient_data'}
        
        # 获取当前数据
        primary_current = data_dict[primary_tf].iloc[current_idx[primary_tf]]
        secondary_current = data_dict[secondary_tf].iloc[current_idx[secondary_tf]]
        entry_current = data_dict[entry_tf].iloc[current_idx[entry_tf]]
        
        # 主时间框架趋势分析
        primary_trend = self.analyze_trend(data_dict[primary_tf], current_idx[primary_tf], params)
        secondary_trend = self.analyze_trend(data_dict[secondary_tf], current_idx[secondary_tf], params)
        
        # 信号强度计算
        signal_strength = 0
        signal_reasons = []
        
        # 1. 主时间框架趋势确认 (权重40%)
        if primary_trend['direction'] == 1:  # 上升趋势
            signal_strength += 0.4 * primary_trend['strength']
            signal_reasons.append(f"{primary_tf}_uptrend")
        elif primary_trend['direction'] == -1:  # 下降趋势
            signal_strength -= 0.4 * primary_trend['strength']
            signal_reasons.append(f"{primary_tf}_downtrend")
        
        # 2. 次级时间框架确认 (权重30%)
        if secondary_trend['direction'] == primary_trend['direction']:
            signal_strength += 0.3 * secondary_trend['strength'] * np.sign(primary_trend['direction'])
            signal_reasons.append(f"{secondary_tf}_confirm")
        else:
            signal_strength -= 0.2 * secondary_trend['strength']
            signal_reasons.append(f"{secondary_tf}_diverge")
        
        # 3. 入场时间框架技术指标 (权重20%)
        entry_score = self.calculate_entry_score(entry_current, params)
        signal_strength += 0.2 * entry_score
        signal_reasons.append(f"{entry_tf}_entry_score_{entry_score:.2f}")
        
        # 4. 成交量确认 (权重10%)
        volume_score = self.calculate_volume_score(data_dict, mtf_config, current_idx, params)
        signal_strength += 0.1 * volume_score
        signal_reasons.append(f"volume_score_{volume_score:.2f}")
        
        # 生成最终信号
        if signal_strength > params['signal_strength_threshold']:
            final_signal = 1
        elif signal_strength < -params['signal_strength_threshold']:
            final_signal = -1
        else:
            final_signal = 0
        
        return {
            'signal': final_signal,
            'strength': signal_strength,
            'reasons': signal_reasons,
            'primary_trend': primary_trend,
            'secondary_trend': secondary_trend
        }
    
    def analyze_trend(self, data: pd.DataFrame, current_idx: int, params: dict) -> dict:
        """分析趋势"""
        if current_idx < params['trend_confirmation_periods']:
            return {'direction': 0, 'strength': 0}
        
        current = data.iloc[current_idx]
        
        # 趋势方向判断
        trend_conditions = [
            current['ema_8'] > current['ema_21'],
            current['ema_21'] > current['ema_55'],
            current['close'] > current['bb_middle'],
            current['rsi'] > 50,
            current['macd'] > current['macd_signal'],
            current.get('momentum_5', 0) > 0,
            current.get('trend_strength', 0) > 0.01
        ]
        
        trend_score = sum(trend_conditions) / len(trend_conditions)
        
        if trend_score > 0.6:
            direction = 1  # 上升趋势
        elif trend_score < 0.4:
            direction = -1  # 下降趋势
        else:
            direction = 0  # 震荡
        
        # 趋势强度
        strength = abs(trend_score - 0.5) * 2  # 0-1之间
        
        return {'direction': direction, 'strength': strength}
    
    def calculate_entry_score(self, current_data: pd.Series, params: dict) -> float:
        """计算入场分数"""
        score = 0
        
        # RSI位置
        if 30 < current_data.get('rsi', 50) < 70:
            score += 0.3
        
        # MACD信号
        if current_data.get('macd', 0) > current_data.get('macd_signal', 0):
            score += 0.2
        
        # 布林带位置
        if current_data.get('bb_lower', 0) < current_data.get('close', 0) < current_data.get('bb_upper', 0):
            score += 0.2
        
        # 动量
        if current_data.get('momentum_5', 0) > params['momentum_threshold']:
            score += 0.3
        
        return score
    
    def calculate_volume_score(self, data_dict: dict, mtf_config: dict, current_idx: dict, params: dict) -> float:
        """计算成交量分数"""
        score = 0
        
        for tf in [mtf_config['primary'], mtf_config['secondary'], mtf_config['entry']]:
            if tf in data_dict and current_idx[tf] < len(data_dict[tf]):
                current = data_dict[tf].iloc[current_idx[tf]]
                volume_ratio = current.get('volume_ratio', 1)
                
                if volume_ratio > params['volume_confirmation']:
                    score += 0.33
        
        return score
    
    def backtest_mtf_strategy(self, mtf_config: dict, params: dict) -> dict:
        """回测多时间框架策略"""
        timeframes = [mtf_config['primary'], mtf_config['secondary'], mtf_config['entry']]
        data_dict = self.get_multi_timeframe_data(timeframes)
        
        if len(data_dict) < 3:
            return {'total_return': -999, 'win_rate': 0, 'total_trades': 0}
        
        # 找到共同的时间范围
        min_length = min(len(data) for data in data_dict.values())
        if min_length < 100:
            return {'total_return': -999, 'win_rate': 0, 'total_trades': 0}
        
        # 初始化
        capital = 10000
        position = 0
        entry_price = 0
        entry_time = None
        
        trades = []
        equity = [capital]
        
        # 回测循环
        start_idx = max(55, min_length // 4)
        
        for i in range(start_idx, min_length - 1):
            current_idx = {tf: min(i, len(data_dict[tf]) - 1) for tf in timeframes}
            
            # 生成多时间框架信号
            signal_info = self.generate_mtf_signal(data_dict, mtf_config, params, current_idx)
            signal = signal_info['signal']
            
            # 获取当前价格和时间
            entry_data = data_dict[mtf_config['entry']].iloc[current_idx[mtf_config['entry']]]
            current_price = entry_data['close']
            current_time = entry_data['datetime']
            
            # 处理开仓
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = current_time
            
            # 处理平仓
            elif position != 0:
                should_close = False
                close_reason = ""
                
                # 动态止损止盈
                atr_value = entry_data.get('atr', current_price * 0.02)
                
                if position == 1:  # 多头
                    stop_loss = entry_price - (atr_value * 2)
                    take_profit = entry_price + (atr_value * 3)
                    
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = "止损"
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = "止盈"
                else:  # 空头
                    stop_loss = entry_price + (atr_value * 2)
                    take_profit = entry_price - (atr_value * 3)
                    
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
                
                # 时间止损
                if entry_time and (current_time - entry_time).total_seconds() / 3600 > 72:  # 72小时
                    should_close = True
                    close_reason = "超时"
                
                # 执行平仓
                if should_close:
                    if position == 1:
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    pnl_amount = capital * 0.15 * pnl_pct  # 15%仓位
                    capital += pnl_amount
                    
                    trades.append({
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'reason': close_reason,
                        'duration_hours': (current_time - entry_time).total_seconds() / 3600,
                        'signal_strength': signal_info['strength']
                    })
                    
                    position = 0
                    entry_price = 0
                    entry_time = None
            
            # 更新权益曲线
            if position != 0 and entry_price > 0:
                if position == 1:
                    unrealized_pnl = capital * 0.15 * ((current_price - entry_price) / entry_price)
                else:
                    unrealized_pnl = capital * 0.15 * ((entry_price - current_price) / entry_price)
                equity.append(capital + unrealized_pnl)
            else:
                equity.append(capital)
        
        # 计算结果
        if not trades:
            return {'total_return': -999, 'win_rate': 0, 'total_trades': 0}
        
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
            'avg_signal_strength': np.mean([t['signal_strength'] for t in trades]),
            'profit_factor': abs(np.mean([t['pnl_amount'] for t in winning_trades]) / 
                               np.mean([t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0])) if len([t for t in trades if t['pnl_amount'] <= 0]) > 0 else 0
        }
    
    def optimize_mtf_combination(self, mtf_config: dict, max_combinations: int = 100):
        """优化多时间框架组合"""
        print(f"\n🎯 优化 {mtf_config['primary']}-{mtf_config['secondary']}-{mtf_config['entry']} 组合...")
        
        # 生成参数组合
        param_names = list(self.optimization_params.keys())
        param_values = list(self.optimization_params.values())
        
        all_combinations = list(itertools.product(*param_values))
        if len(all_combinations) > max_combinations:
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
            
            result = self.backtest_mtf_strategy(mtf_config, params)
            
            if result['total_return'] > best_result['total_return']:
                best_result = result
                best_params = params
            
            if (i + 1) % 20 == 0:
                print(f"   进度: {i+1}/{len(combinations)} ({(i+1)/len(combinations)*100:.1f}%)")
        
        return {
            'mtf_config': mtf_config,
            'best_params': best_params,
            'best_result': best_result
        }
    
    def run_comprehensive_optimization(self):
        """运行全面优化"""
        print("🚀 DOGE/USDT 多时间框架策略优化")
        print("=" * 60)
        
        results = {}
        
        for i, mtf_config in enumerate(self.mtf_combinations):
            print(f"\n📊 优化组合 {i+1}/{len(self.mtf_combinations)}")
            result = self.optimize_mtf_combination(mtf_config)
            if result:
                config_name = f"{mtf_config['primary']}_{mtf_config['secondary']}_{mtf_config['entry']}"
                results[config_name] = result
        
        # 生成优化报告
        self.generate_optimization_report(results)
        
        return results
    
    def generate_optimization_report(self, results: dict):
        """生成优化报告"""
        print("\n" + "=" * 60)
        print("📊 DOGE/USDT 多时间框架策略优化报告")
        print("=" * 60)
        
        # 按收益率排序
        sorted_results = sorted(results.items(), key=lambda x: x[1]['best_result']['total_return'], reverse=True)
        
        print(f"\n🏆 最佳多时间框架组合 (Top {min(5, len(sorted_results))}):")
        print(f"{'排名':<4} {'组合':<20} {'收益率':<10} {'胜率':<8} {'交易数':<8} {'最大回撤':<10}")
        print("-" * 70)
        
        for i, (config_name, result) in enumerate(sorted_results[:5], 1):
            best_result = result['best_result']
            print(f"{i:<4} {config_name:<20} {best_result['total_return']:<10.2f}% "
                  f"{best_result['win_rate']:<8.1f}% {best_result['total_trades']:<8} "
                  f"{best_result['max_drawdown']:<10.2f}%")
        
        # 详细分析最佳组合
        if sorted_results:
            best_config_name, best_result = sorted_results[0]
            print(f"\n🎯 最佳组合详细分析: {best_config_name}")
            print(f"   时间框架组合: {best_result['mtf_config']}")
            print(f"   收益率: {best_result['best_result']['total_return']:.2f}%")
            print(f"   胜率: {best_result['best_result']['win_rate']:.1f}%")
            print(f"   交易次数: {best_result['best_result']['total_trades']}")
            print(f"   平均持仓时间: {best_result['best_result']['avg_duration']:.1f} 小时")
            print(f"   平均信号强度: {best_result['best_result']['avg_signal_strength']:.3f}")
            print(f"   盈亏比: {best_result['best_result']['profit_factor']:.2f}")
            
            print(f"   最佳参数:")
            for param, value in best_result['best_params'].items():
                print(f"     {param}: {value}")
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        optimization_data = []
        for config_name, result in results.items():
            if result:
                row = {
                    'config_name': config_name,
                    'primary_tf': result['mtf_config']['primary'],
                    'secondary_tf': result['mtf_config']['secondary'],
                    'entry_tf': result['mtf_config']['entry'],
                    'total_return': result['best_result']['total_return'],
                    'win_rate': result['best_result']['win_rate'],
                    'total_trades': result['best_result']['total_trades'],
                    'max_drawdown': result['best_result']['max_drawdown'],
                    'avg_duration': result['best_result']['avg_duration'],
                    'avg_signal_strength': result['best_result']['avg_signal_strength'],
                    'profit_factor': result['best_result']['profit_factor']
                }
                
                # 添加最佳参数
                for param, value in result['best_params'].items():
                    row[f'param_{param}'] = value
                
                optimization_data.append(row)
        
        if optimization_data:
            os.makedirs('results', exist_ok=True)
            results_df = pd.DataFrame(optimization_data)
            results_file = f'results/doge_mtf_optimization_{timestamp}.csv'
            results_df.to_csv(results_file, index=False)
            print(f"\n💾 优化结果已保存: {results_file}")


def main():
    """主函数"""
    print("🐕 DOGE/USDT 多时间框架深度策略优化系统")
    print("基于多时间框架信号融合的高级策略")
    print("=" * 60)
    
    optimizer = DOGEMultiTimeframeOptimizer()
    results = optimizer.run_comprehensive_optimization()
    
    print(f"\n🎉 DOGE/USDT 多时间框架策略优化完成!")


if __name__ == "__main__":
    main()
