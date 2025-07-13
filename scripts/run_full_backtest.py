#!/usr/bin/env python3
"""
完整数据回测脚本
使用真实的历史数据进行回测，解决30条数据限制问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# 导入模块
from modules.enhanced_data_module import EnhancedDataModule
from strategies.scalping_strategy import ScalpingStrategy
from modules.risk_module import RiskModule
from modules.log_module import LogModule

class FullBacktester:
    """完整数据回测器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        self.risk_module = RiskModule(initial_capital=10000)
        self.logger = LogModule()
        
        # 回测配置
        self.config = {
            'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT'],
            'timeframes': ['1d', '4h', '1h'],
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'initial_capital': 10000,
            'max_positions': 3
        }
        
        # 结果存储
        self.results = {}
        self.trades = []
        self.equity_curve = []
    
    def run_backtest(self, symbol: str, timeframe: str = '1d'):
        """运行单个交易对的回测"""
        print(f"\n🔍 回测 {symbol} ({timeframe})")
        
        try:
            # 获取历史数据
            data = self.data_module.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=self.config['start_date'],
                end_date=self.config['end_date']
            )
            
            if data.empty or len(data) < 100:
                print(f"❌ {symbol} 数据不足: {len(data)} 条")
                return None
            
            print(f"✅ 数据加载成功: {len(data)} 条")
            print(f"   时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
            
            # 初始化策略
            strategy = ScalpingStrategy()
            
            # 计算技术指标
            data = self._calculate_indicators(data)
            
            # 执行回测
            results = self._execute_backtest(data, strategy, symbol, timeframe)
            
            return results
            
        except Exception as e:
            print(f"❌ 回测失败 {symbol}: {str(e)}")
            return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # EMA指标
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_55'] = df['close'].ewm(span=55).mean()
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # ATR (用于止损)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def _execute_backtest(self, data: pd.DataFrame, strategy, symbol: str, timeframe: str) -> dict:
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
        
        # 遍历数据
        for i in range(55, len(data)):  # 从55开始，确保指标计算完整
            current = data.iloc[i]
            
            # 跳过指标不完整的数据
            if pd.isna(current['ema_55']) or pd.isna(current['rsi']) or pd.isna(current['atr']):
                equity.append(equity[-1])
                continue
            
            # 生成交易信号
            signal = self._generate_signal(data.iloc[i-10:i+1])  # 使用最近10条数据
            
            current_time = current['datetime']
            current_price = current['close']
            
            # 处理开仓信号
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = current_time
                
                # 设置止损止盈
                atr_value = current['atr']
                if signal == 1:  # 多头
                    stop_loss = entry_price - (atr_value * 2)
                    take_profit = entry_price + (atr_value * 4)  # 2:1盈亏比
                else:  # 空头
                    stop_loss = entry_price + (atr_value * 2)
                    take_profit = entry_price - (atr_value * 4)
                
                print(f"   📈 开仓: {signal} @ {entry_price:.2f} ({current_time})")
            
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
                
                # 最大持仓时间 (根据时间框架调整)
                max_hold_hours = {'1h': 24, '4h': 96, '1d': 240}
                max_hold = max_hold_hours.get(timeframe, 240)
                
                if (current_time - entry_time).total_seconds() / 3600 > max_hold:
                    should_close = True
                    close_reason = "超时"
                
                # 执行平仓
                if should_close:
                    # 计算盈亏
                    if position == 1:
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    pnl_amount = capital * 0.01 * pnl_pct * 100  # 1%仓位
                    capital += pnl_amount
                    
                    # 记录交易
                    trade = {
                        'symbol': symbol,
                        'timeframe': timeframe,
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
                    
                    print(f"   📉 平仓: {position} @ {current_price:.2f} | 盈亏: {pnl_pct*100:.2f}% | {close_reason}")
                    
                    # 重置仓位
                    position = 0
                    entry_price = 0
                    entry_time = None
            
            # 更新权益曲线
            equity.append(capital)
        
        # 计算回测结果
        results = self._calculate_results(trades, equity, symbol, timeframe)
        
        return results
    
    def _generate_signal(self, data: pd.DataFrame) -> int:
        """生成交易信号"""
        if len(data) < 2:
            return 0
        
        current = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 多头信号条件
        long_conditions = [
            current['ema_8'] > current['ema_21'],  # 短期EMA > 中期EMA
            current['ema_21'] > current['ema_55'],  # 中期EMA > 长期EMA
            current['close'] > current['bb_middle'],  # 价格在布林带中轨上方
            current['rsi'] > 30 and current['rsi'] < 70,  # RSI在合理区间
            current['macd'] > current['macd_signal'],  # MACD金叉
            current['close'] > prev['close']  # 价格上涨
        ]
        
        # 空头信号条件
        short_conditions = [
            current['ema_8'] < current['ema_21'],  # 短期EMA < 中期EMA
            current['ema_21'] < current['ema_55'],  # 中期EMA < 长期EMA
            current['close'] < current['bb_middle'],  # 价格在布林带中轨下方
            current['rsi'] > 30 and current['rsi'] < 70,  # RSI在合理区间
            current['macd'] < current['macd_signal'],  # MACD死叉
            current['close'] < prev['close']  # 价格下跌
        ]
        
        # 信号强度计算
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        # 需要至少4个条件满足才开仓
        if long_score >= 4:
            return 1  # 多头信号
        elif short_score >= 4:
            return -1  # 空头信号
        else:
            return 0  # 无信号
    
    def _calculate_results(self, trades: list, equity: list, symbol: str, timeframe: str) -> dict:
        """计算回测结果"""
        if not trades:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        # 基础统计
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        losing_trades = [t for t in trades if t['pnl_amount'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        # 收益统计
        total_return = (equity[-1] - equity[0]) / equity[0] * 100
        
        # 最大回撤
        peak = equity[0]
        max_dd = 0
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # 夏普比率 (简化计算)
        returns = pd.Series(equity).pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # 平均盈亏
        avg_win = np.mean([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_amount'] for t in losing_trades]) if losing_trades else 0
        
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'final_capital': equity[-1],
            'trades': trades,
            'equity_curve': equity
        }
        
        return results
    
    def run_comprehensive_backtest(self):
        """运行综合回测"""
        print("🚀 开始综合回测...")
        print("=" * 60)
        
        all_results = []
        
        # 测试不同交易对和时间框架
        for symbol in self.config['symbols']:
            for timeframe in self.config['timeframes']:
                result = self.run_backtest(symbol, timeframe)
                if result:
                    all_results.append(result)
        
        # 生成综合报告
        self._generate_report(all_results)
        
        return all_results
    
    def _generate_report(self, results: list):
        """生成回测报告"""
        print("\n" + "=" * 60)
        print("📊 综合回测报告")
        print("=" * 60)
        
        if not results:
            print("❌ 没有有效的回测结果")
            return
        
        # 汇总统计
        total_trades = sum(r['total_trades'] for r in results)
        total_winning = sum(r['winning_trades'] for r in results)
        
        if total_trades > 0:
            overall_win_rate = total_winning / total_trades * 100
            avg_return = np.mean([r['total_return'] for r in results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in results if r['sharpe_ratio'] != 0])
            avg_max_dd = np.mean([r['max_drawdown'] for r in results])
            
            print(f"📈 总体表现:")
            print(f"   总交易次数: {total_trades}")
            print(f"   总体胜率: {overall_win_rate:.2f}%")
            print(f"   平均收益率: {avg_return:.2f}%")
            print(f"   平均夏普比率: {avg_sharpe:.4f}")
            print(f"   平均最大回撤: {avg_max_dd:.2f}%")
        
        print(f"\n📋 详细结果:")
        print(f"{'交易对':<12} {'时间框架':<8} {'交易次数':<8} {'胜率':<8} {'收益率':<10} {'最大回撤':<10}")
        print("-" * 70)
        
        for result in results:
            print(f"{result['symbol']:<12} {result['timeframe']:<8} "
                  f"{result['total_trades']:<8} {result['win_rate']:<8.1f}% "
                  f"{result['total_return']:<10.2f}% {result['max_drawdown']:<10.2f}%")
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存详细结果
        results_df = pd.DataFrame([{
            'symbol': r['symbol'],
            'timeframe': r['timeframe'],
            'total_trades': r['total_trades'],
            'win_rate': r['win_rate'],
            'total_return': r['total_return'],
            'max_drawdown': r['max_drawdown'],
            'sharpe_ratio': r['sharpe_ratio'],
            'final_capital': r['final_capital']
        } for r in results])
        
        os.makedirs('results', exist_ok=True)
        results_file = f'results/full_backtest_results_{timestamp}.csv'
        results_df.to_csv(results_file, index=False)
        
        print(f"\n💾 结果已保存: {results_file}")
        
        # 生成图表
        self._plot_results(results, timestamp)
    
    def _plot_results(self, results: list, timestamp: str):
        """生成结果图表"""
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('TradeFan 完整数据回测结果', fontsize=16)
            
            # 1. 收益率对比
            symbols = [r['symbol'] for r in results]
            returns = [r['total_return'] for r in results]
            
            axes[0, 0].bar(range(len(symbols)), returns)
            axes[0, 0].set_title('各交易对收益率')
            axes[0, 0].set_xlabel('交易对')
            axes[0, 0].set_ylabel('收益率 (%)')
            axes[0, 0].set_xticks(range(len(symbols)))
            axes[0, 0].set_xticklabels([s.split('/')[0] for s in symbols], rotation=45)
            
            # 2. 胜率分布
            win_rates = [r['win_rate'] for r in results]
            axes[0, 1].hist(win_rates, bins=10, alpha=0.7)
            axes[0, 1].set_title('胜率分布')
            axes[0, 1].set_xlabel('胜率 (%)')
            axes[0, 1].set_ylabel('频次')
            
            # 3. 风险收益散点图
            max_dds = [r['max_drawdown'] for r in results]
            axes[1, 0].scatter(max_dds, returns)
            axes[1, 0].set_title('风险收益关系')
            axes[1, 0].set_xlabel('最大回撤 (%)')
            axes[1, 0].set_ylabel('收益率 (%)')
            
            # 4. 交易次数统计
            trade_counts = [r['total_trades'] for r in results]
            timeframes = [r['timeframe'] for r in results]
            
            tf_counts = {}
            for tf, count in zip(timeframes, trade_counts):
                if tf not in tf_counts:
                    tf_counts[tf] = []
                tf_counts[tf].append(count)
            
            tf_names = list(tf_counts.keys())
            tf_means = [np.mean(tf_counts[tf]) for tf in tf_names]
            
            axes[1, 1].bar(tf_names, tf_means)
            axes[1, 1].set_title('各时间框架平均交易次数')
            axes[1, 1].set_xlabel('时间框架')
            axes[1, 1].set_ylabel('平均交易次数')
            
            plt.tight_layout()
            
            chart_file = f'results/full_backtest_chart_{timestamp}.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"📊 图表已保存: {chart_file}")
            
        except Exception as e:
            print(f"⚠️  图表生成失败: {str(e)}")


def main():
    """主函数"""
    print("🚀 TradeFan 完整数据回测系统")
    print("=" * 50)
    
    # 检查数据可用性
    data_module = EnhancedDataModule()
    summary = data_module.get_data_summary()
    
    print(f"📊 数据概况:")
    print(f"   可用文件: {summary['total_files']} 个")
    print(f"   支持币种: {summary['symbols']}")
    print(f"   时间框架: {summary['timeframes']}")
    
    if summary['total_files'] == 0:
        print("\n❌ 没有找到历史数据文件")
        print("💡 请先运行: python3 scripts/fix_data_source.py")
        return
    
    # 运行回测
    backtester = FullBacktester()
    results = backtester.run_comprehensive_backtest()
    
    print(f"\n🎉 回测完成! 共测试了 {len(results)} 个配置")


if __name__ == "__main__":
    main()
