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
#!/usr/bin/env python3
"""
全面回测脚本第二部分 - 性能计算和报告生成
"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import os

class ComprehensiveBacktesterPart2:
    """全面回测器第二部分"""
    
    def _calculate_performance(self, trades: list, equity: list, symbol: str, timeframe: str, data_count: int) -> dict:
        """计算回测性能指标"""
        if not trades:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'no_trades',
                'data_count': data_count,
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'final_capital': equity[-1] if equity else self.config['initial_capital']
            }
        
        # 基础统计
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        losing_trades = [t for t in trades if t['pnl_amount'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # 收益统计
        initial_capital = self.config['initial_capital']
        final_capital = equity[-1] if equity else initial_capital
        total_return = (final_capital - initial_capital) / initial_capital * 100
        
        # 最大回撤
        peak = initial_capital
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 夏普比率 (简化计算)
        if len(equity) > 1:
            returns = pd.Series(equity).pct_change().dropna()
            if returns.std() > 0:
                # 根据时间框架调整年化因子
                timeframe_factors = {
                    '5m': 105120,   # 5分钟 * 12 * 24 * 365
                    '15m': 35040,   # 15分钟 * 4 * 24 * 365
                    '30m': 17520,   # 30分钟 * 2 * 24 * 365
                    '1h': 8760,     # 1小时 * 24 * 365
                    '4h': 2190,     # 4小时 * 6 * 365
                    '1d': 365       # 1天 * 365
                }
                factor = timeframe_factors.get(timeframe, 365)
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(factor)
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # 平均盈亏
        avg_win = np.mean([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_amount'] for t in losing_trades]) if losing_trades else 0
        
        # 盈亏比
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 平均持仓时间
        avg_duration = np.mean([t['duration_hours'] for t in trades]) if trades else 0
        
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'status': 'success',
            'data_count': data_count,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_duration_hours': avg_duration,
            'final_capital': final_capital,
            'trades': trades,
            'equity_curve': equity
        }
        
        return results
    
    def run_comprehensive_backtest(self):
        """运行全面回测"""
        print("🚀 开始全面回测分析...")
        print("=" * 80)
        print(f"📊 测试配置:")
        print(f"   币种数量: {len(self.config['symbols'])} 个")
        print(f"   时间框架: {len(self.config['timeframes'])} 个")
        print(f"   总配置数: {len(self.config['symbols']) * len(self.config['timeframes'])} 个")
        
        all_results = []
        
        # 使用多线程加速回测
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有回测任务
            future_to_config = {}
            for symbol in self.config['symbols']:
                for timeframe in self.config['timeframes']:
                    future = executor.submit(self.execute_backtest, symbol, timeframe)
                    future_to_config[future] = (symbol, timeframe)
            
            # 收集结果
            completed = 0
            total_tasks = len(future_to_config)
            
            for future in as_completed(future_to_config):
                symbol, timeframe = future_to_config[future]
                completed += 1
                
                try:
                    result = future.result()
                    all_results.append(result)
                    
                    # 显示进度
                    status = result.get('status', 'unknown')
                    if status == 'success':
                        trades = result.get('total_trades', 0)
                        returns = result.get('total_return', 0)
                        print(f"   ✅ {symbol:<12} {timeframe:<4} | {trades:>3}笔 | {returns:>6.2f}% | ({completed}/{total_tasks})")
                    elif status == 'insufficient_data':
                        data_count = result.get('data_count', 0)
                        print(f"   ⚠️  {symbol:<12} {timeframe:<4} | 数据不足: {data_count}条 | ({completed}/{total_tasks})")
                    else:
                        error = result.get('error', 'Unknown error')[:30]
                        print(f"   ❌ {symbol:<12} {timeframe:<4} | 错误: {error} | ({completed}/{total_tasks})")
                        
                except Exception as e:
                    print(f"   ❌ {symbol:<12} {timeframe:<4} | 异常: {str(e)[:30]} | ({completed}/{total_tasks})")
        
        # 生成综合报告
        self._generate_comprehensive_report(all_results)
        
        return all_results
    
    def _generate_comprehensive_report(self, results: list):
        """生成综合回测报告"""
        print("\n" + "=" * 80)
        print("📊 全面回测报告")
        print("=" * 80)
        
        # 过滤成功的结果
        successful_results = [r for r in results if r.get('status') == 'success' and r.get('total_trades', 0) > 0]
        
        if not successful_results:
            print("❌ 没有成功的回测结果")
            return
        
        # 1. 总体统计
        total_configs = len(results)
        successful_configs = len(successful_results)
        success_rate = successful_configs / total_configs * 100
        
        print(f"📈 总体统计:")
        print(f"   测试配置: {total_configs} 个")
        print(f"   成功配置: {successful_configs} 个")
        print(f"   成功率: {success_rate:.1f}%")
        
        # 2. 按币种统计
        print(f"\n💰 按币种统计:")
        symbol_stats = {}
        for result in successful_results:
            symbol = result['symbol']
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'configs': 0,
                    'total_trades': 0,
                    'avg_return': 0,
                    'avg_win_rate': 0,
                    'returns': []
                }
            
            symbol_stats[symbol]['configs'] += 1
            symbol_stats[symbol]['total_trades'] += result['total_trades']
            symbol_stats[symbol]['returns'].append(result['total_return'])
        
        # 计算平均值
        for symbol, stats in symbol_stats.items():
            stats['avg_return'] = np.mean(stats['returns'])
            stats['best_return'] = max(stats['returns'])
            stats['worst_return'] = min(stats['returns'])
        
        # 按平均收益率排序
        sorted_symbols = sorted(symbol_stats.items(), key=lambda x: x[1]['avg_return'], reverse=True)
        
        print(f"{'币种':<12} {'配置数':<6} {'总交易':<8} {'平均收益':<10} {'最佳收益':<10} {'最差收益':<10}")
        print("-" * 70)
        for symbol, stats in sorted_symbols:
            print(f"{symbol:<12} {stats['configs']:<6} {stats['total_trades']:<8} "
                  f"{stats['avg_return']:<10.2f}% {stats['best_return']:<10.2f}% {stats['worst_return']:<10.2f}%")
        
        # 3. 按时间框架统计
        print(f"\n⏰ 按时间框架统计:")
        timeframe_stats = {}
        for result in successful_results:
            tf = result['timeframe']
            if tf not in timeframe_stats:
                timeframe_stats[tf] = {
                    'configs': 0,
                    'total_trades': 0,
                    'returns': [],
                    'win_rates': [],
                    'sharpe_ratios': []
                }
            
            timeframe_stats[tf]['configs'] += 1
            timeframe_stats[tf]['total_trades'] += result['total_trades']
            timeframe_stats[tf]['returns'].append(result['total_return'])
            timeframe_stats[tf]['win_rates'].append(result['win_rate'])
            timeframe_stats[tf]['sharpe_ratios'].append(result['sharpe_ratio'])
        
        # 计算平均值
        for tf, stats in timeframe_stats.items():
            stats['avg_return'] = np.mean(stats['returns'])
            stats['avg_win_rate'] = np.mean(stats['win_rates'])
            stats['avg_sharpe'] = np.mean(stats['sharpe_ratios'])
        
        # 按平均收益率排序
        sorted_timeframes = sorted(timeframe_stats.items(), key=lambda x: x[1]['avg_return'], reverse=True)
        
        print(f"{'时间框架':<8} {'配置数':<6} {'总交易':<8} {'平均收益':<10} {'平均胜率':<10} {'平均夏普':<10}")
        print("-" * 70)
        for tf, stats in sorted_timeframes:
            print(f"{tf:<8} {stats['configs']:<6} {stats['total_trades']:<8} "
                  f"{stats['avg_return']:<10.2f}% {stats['avg_win_rate']:<10.1f}% {stats['avg_sharpe']:<10.3f}")
        
        # 4. 最佳表现配置
        print(f"\n🏆 最佳表现配置 (Top 10):")
        best_results = sorted(successful_results, key=lambda x: x['total_return'], reverse=True)[:10]
        
        print(f"{'排名':<4} {'币种':<12} {'时间框架':<8} {'交易数':<6} {'胜率':<8} {'收益率':<10} {'夏普比率':<10}")
        print("-" * 75)
        for i, result in enumerate(best_results, 1):
            print(f"{i:<4} {result['symbol']:<12} {result['timeframe']:<8} "
                  f"{result['total_trades']:<6} {result['win_rate']:<8.1f}% "
                  f"{result['total_return']:<10.2f}% {result['sharpe_ratio']:<10.3f}")
        
        # 5. 风险分析
        print(f"\n⚠️  风险分析:")
        all_returns = [r['total_return'] for r in successful_results]
        all_drawdowns = [r['max_drawdown'] for r in successful_results]
        
        print(f"   收益率分布:")
        print(f"     平均: {np.mean(all_returns):.2f}%")
        print(f"     中位数: {np.median(all_returns):.2f}%")
        print(f"     标准差: {np.std(all_returns):.2f}%")
        print(f"     最大: {max(all_returns):.2f}%")
        print(f"     最小: {min(all_returns):.2f}%")
        
        print(f"   最大回撤分布:")
        print(f"     平均: {np.mean(all_drawdowns):.2f}%")
        print(f"     中位数: {np.median(all_drawdowns):.2f}%")
        print(f"     最大: {max(all_drawdowns):.2f}%")
        
        # 保存结果
        self._save_results(results, successful_results)
        
        # 生成图表
        self._generate_charts(successful_results)
    
    def _save_results(self, all_results: list, successful_results: list):
        """保存回测结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs('results', exist_ok=True)
        
        # 保存详细结果
        detailed_results = []
        for result in all_results:
            detailed_results.append({
                'symbol': result.get('symbol', ''),
                'timeframe': result.get('timeframe', ''),
                'status': result.get('status', ''),
                'data_count': result.get('data_count', 0),
                'total_trades': result.get('total_trades', 0),
                'win_rate': result.get('win_rate', 0),
                'total_return': result.get('total_return', 0),
                'max_drawdown': result.get('max_drawdown', 0),
                'sharpe_ratio': result.get('sharpe_ratio', 0),
                'final_capital': result.get('final_capital', 0)
            })
        
        results_df = pd.DataFrame(detailed_results)
        results_file = f'results/comprehensive_backtest_{timestamp}.csv'
        results_df.to_csv(results_file, index=False)
        
        print(f"\n💾 结果已保存: {results_file}")
        
        # 保存成功配置的交易详情
        if successful_results:
            trades_data = []
            for result in successful_results:
                for trade in result.get('trades', []):
                    trade_record = trade.copy()
                    trade_record['symbol'] = result['symbol']
                    trade_record['timeframe'] = result['timeframe']
                    trades_data.append(trade_record)
            
            if trades_data:
                trades_df = pd.DataFrame(trades_data)
                trades_file = f'results/comprehensive_trades_{timestamp}.csv'
                trades_df.to_csv(trades_file, index=False)
                print(f"💾 交易详情已保存: {trades_file}")
    
    def _generate_charts(self, successful_results: list):
        """生成分析图表"""
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            fig.suptitle('TradeFan 全面回测分析报告', fontsize=16)
            
            # 1. 收益率分布
            returns = [r['total_return'] for r in successful_results]
            axes[0, 0].hist(returns, bins=20, alpha=0.7, color='skyblue')
            axes[0, 0].set_title('收益率分布')
            axes[0, 0].set_xlabel('收益率 (%)')
            axes[0, 0].set_ylabel('频次')
            axes[0, 0].axvline(np.mean(returns), color='red', linestyle='--', label=f'平均: {np.mean(returns):.2f}%')
            axes[0, 0].legend()
            
            # 2. 按币种收益对比
            symbol_returns = {}
            for result in successful_results:
                symbol = result['symbol'].split('/')[0]  # 只取币种名称
                if symbol not in symbol_returns:
                    symbol_returns[symbol] = []
                symbol_returns[symbol].append(result['total_return'])
            
            symbols = list(symbol_returns.keys())
            avg_returns = [np.mean(symbol_returns[s]) for s in symbols]
            
            axes[0, 1].bar(symbols, avg_returns, color='lightgreen')
            axes[0, 1].set_title('各币种平均收益率')
            axes[0, 1].set_xlabel('币种')
            axes[0, 1].set_ylabel('平均收益率 (%)')
            axes[0, 1].tick_params(axis='x', rotation=45)
            
            # 3. 按时间框架收益对比
            tf_returns = {}
            for result in successful_results:
                tf = result['timeframe']
                if tf not in tf_returns:
                    tf_returns[tf] = []
                tf_returns[tf].append(result['total_return'])
            
            timeframes = list(tf_returns.keys())
            tf_avg_returns = [np.mean(tf_returns[tf]) for tf in timeframes]
            
            axes[0, 2].bar(timeframes, tf_avg_returns, color='orange')
            axes[0, 2].set_title('各时间框架平均收益率')
            axes[0, 2].set_xlabel('时间框架')
            axes[0, 2].set_ylabel('平均收益率 (%)')
            
            # 4. 胜率vs收益率散点图
            win_rates = [r['win_rate'] for r in successful_results]
            axes[1, 0].scatter(win_rates, returns, alpha=0.6)
            axes[1, 0].set_title('胜率 vs 收益率')
            axes[1, 0].set_xlabel('胜率 (%)')
            axes[1, 0].set_ylabel('收益率 (%)')
            
            # 5. 最大回撤分布
            drawdowns = [r['max_drawdown'] for r in successful_results]
            axes[1, 1].hist(drawdowns, bins=15, alpha=0.7, color='salmon')
            axes[1, 1].set_title('最大回撤分布')
            axes[1, 1].set_xlabel('最大回撤 (%)')
            axes[1, 1].set_ylabel('频次')
            axes[1, 1].axvline(np.mean(drawdowns), color='red', linestyle='--', label=f'平均: {np.mean(drawdowns):.2f}%')
            axes[1, 1].legend()
            
            # 6. 夏普比率分布
            sharpe_ratios = [r['sharpe_ratio'] for r in successful_results if abs(r['sharpe_ratio']) < 10]  # 过滤异常值
            if sharpe_ratios:
                axes[1, 2].hist(sharpe_ratios, bins=15, alpha=0.7, color='gold')
                axes[1, 2].set_title('夏普比率分布')
                axes[1, 2].set_xlabel('夏普比率')
                axes[1, 2].set_ylabel('频次')
                axes[1, 2].axvline(np.mean(sharpe_ratios), color='red', linestyle='--', label=f'平均: {np.mean(sharpe_ratios):.3f}')
                axes[1, 2].legend()
            
            plt.tight_layout()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_file = f'results/comprehensive_analysis_{timestamp}.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 分析图表已保存: {chart_file}")
            
        except Exception as e:
            print(f"⚠️  图表生成失败: {str(e)}")


def main():
    """主函数"""
    print("🚀 TradeFan 全面回测系统")
    print("支持7个币种 × 6个时间框架 = 42种配置")
    print("=" * 80)
    
    # 检查数据可用性
    from modules.enhanced_data_module import EnhancedDataModule
    data_module = EnhancedDataModule()
    summary = data_module.get_data_summary()
    
    print(f"📊 数据概况:")
    print(f"   可用文件: {summary['total_files']} 个")
    print(f"   支持币种: {len(summary['symbols'])} 个")
    print(f"   时间框架: {len(summary['timeframes'])} 个")
    
    if summary['total_files'] < 20:
        print("\n⚠️  数据文件较少，建议先运行数据获取脚本")
        print("💡 运行: python3 scripts/enhanced_data_source.py")
        return
    
    # 创建回测器并运行
    class ComprehensiveBacktester(ComprehensiveBacktesterPart2):
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
    
    backtester = ComprehensiveBacktester()
    results = backtester.run_comprehensive_backtest()
    
    print(f"\n🎉 全面回测完成!")
    print(f"   总配置: {len(results)} 个")
    print(f"   成功配置: {len([r for r in results if r.get('status') == 'success'])} 个")


if __name__ == "__main__":
    main()
