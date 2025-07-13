#!/usr/bin/env python3
"""
简化完整数据回测脚本
使用真实的历史数据进行回测，解决30条数据限制问题
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入模块
from modules.enhanced_data_module import EnhancedDataModule

class SimpleBacktester:
    """简化回测器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        
        # 回测配置
        self.config = {
            'symbols': ['BTC/USDT', 'ETH/USDT'],
            'timeframes': ['1d'],
            'start_date': '2024-01-01',
            'end_date': '2024-06-30',
            'initial_capital': 10000
        }
    
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
            print(f"   价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
            
            # 计算技术指标
            data = self._calculate_indicators(data)
            
            # 执行简单回测
            results = self._execute_simple_backtest(data, symbol, timeframe)
            
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
        
        # ATR (用于止损)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def _execute_simple_backtest(self, data: pd.DataFrame, symbol: str, timeframe: str) -> dict:
        """执行简单回测逻辑"""
        
        # 初始化变量
        capital = self.config['initial_capital']
        position = 0  # 0: 无仓位, 1: 多头
        entry_price = 0
        entry_time = None
        
        trades = []
        equity = [capital]
        
        print(f"   📊 开始回测分析...")
        
        # 遍历数据
        for i in range(55, len(data)):  # 从55开始，确保指标计算完整
            current = data.iloc[i]
            
            # 跳过指标不完整的数据
            if pd.isna(current['ema_55']) or pd.isna(current['rsi']) or pd.isna(current['atr']):
                equity.append(equity[-1])
                continue
            
            current_time = current['datetime']
            current_price = current['close']
            
            # 简单的买入持有策略 + 技术指标过滤
            if position == 0:  # 无仓位时考虑买入
                # 买入条件：价格上升趋势 + RSI不超买
                if (current['ema_8'] > current['ema_21'] and 
                    current['ema_21'] > current['ema_55'] and
                    current['rsi'] < 70 and current['rsi'] > 30):
                    
                    position = 1
                    entry_price = current_price
                    entry_time = current_time
                    
                    print(f"   📈 买入: @ {entry_price:.2f} ({current_time.strftime('%Y-%m-%d')})")
            
            elif position == 1:  # 持仓时考虑卖出
                # 卖出条件：下降趋势 或 RSI超买 或 止损
                stop_loss = entry_price * 0.95  # 5%止损
                
                if (current['ema_8'] < current['ema_21'] or 
                    current['rsi'] > 75 or 
                    current_price < stop_loss):
                    
                    # 计算盈亏
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    pnl_amount = capital * 0.1 * (pnl_pct / 100)  # 10%仓位
                    capital += pnl_amount
                    
                    # 记录交易
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'duration_days': (current_time - entry_time).days
                    }
                    trades.append(trade)
                    
                    print(f"   📉 卖出: @ {current_price:.2f} | 盈亏: {pnl_pct:.2f}% | 持有: {trade['duration_days']}天")
                    
                    # 重置仓位
                    position = 0
                    entry_price = 0
                    entry_time = None
            
            # 更新权益曲线
            if position == 1:
                # 持仓时按当前价格计算浮盈浮亏
                unrealized_pnl = capital * 0.1 * ((current_price - entry_price) / entry_price)
                equity.append(capital + unrealized_pnl)
            else:
                equity.append(capital)
        
        # 计算回测结果
        results = self._calculate_results(trades, equity, symbol, timeframe)
        
        return results
    
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
                'final_capital': equity[-1] if equity else self.config['initial_capital']
            }
        
        # 基础统计
        total_trades = len(trades)
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        
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
        
        # 平均盈亏
        avg_win = np.mean([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0]) if trades else 0
        
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_dd,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'final_capital': equity[-1],
            'trades': trades,
            'equity_curve': equity
        }
        
        return results
    
    def run_comprehensive_backtest(self):
        """运行综合回测"""
        print("🚀 开始简化综合回测...")
        print("=" * 60)
        
        all_results = []
        
        # 测试不同交易对
        for symbol in self.config['symbols']:
            for timeframe in self.config['timeframes']:
                result = self.run_backtest(symbol, timeframe)
                if result:
                    all_results.append(result)
        
        # 生成报告
        self._generate_report(all_results)
        
        return all_results
    
    def _generate_report(self, results: list):
        """生成回测报告"""
        print("\n" + "=" * 60)
        print("📊 简化回测报告")
        print("=" * 60)
        
        if not results:
            print("❌ 没有有效的回测结果")
            return
        
        print(f"📋 详细结果:")
        print(f"{'交易对':<12} {'交易次数':<8} {'胜率':<8} {'收益率':<10} {'最大回撤':<10} {'最终资金':<12}")
        print("-" * 75)
        
        total_final_capital = 0
        
        for result in results:
            print(f"{result['symbol']:<12} {result['total_trades']:<8} "
                  f"{result['win_rate']:<8.1f}% {result['total_return']:<10.2f}% "
                  f"{result['max_drawdown']:<10.2f}% ${result['final_capital']:<12.2f}")
            
            total_final_capital += result['final_capital']
        
        # 汇总统计
        initial_total = len(results) * self.config['initial_capital']
        overall_return = (total_final_capital - initial_total) / initial_total * 100
        
        print("-" * 75)
        print(f"📈 总体表现:")
        print(f"   初始资金: ${initial_total:,.2f}")
        print(f"   最终资金: ${total_final_capital:,.2f}")
        print(f"   总体收益率: {overall_return:.2f}%")
        
        # 保存结果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        results_df = pd.DataFrame([{
            'symbol': r['symbol'],
            'timeframe': r['timeframe'],
            'total_trades': r['total_trades'],
            'win_rate': r['win_rate'],
            'total_return': r['total_return'],
            'max_drawdown': r['max_drawdown'],
            'final_capital': r['final_capital']
        } for r in results])
        
        os.makedirs('results', exist_ok=True)
        results_file = f'results/simple_backtest_results_{timestamp}.csv'
        results_df.to_csv(results_file, index=False)
        
        print(f"\n💾 结果已保存: {results_file}")


def main():
    """主函数"""
    print("🚀 TradeFan 简化完整数据回测系统")
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
    backtester = SimpleBacktester()
    results = backtester.run_comprehensive_backtest()
    
    print(f"\n🎉 回测完成! 共测试了 {len(results)} 个配置")
    
    # 显示一些交易详情
    for result in results:
        if result['trades']:
            print(f"\n📋 {result['symbol']} 交易详情 (前5笔):")
            for i, trade in enumerate(result['trades'][:5]):
                print(f"   {i+1}. {trade['entry_time'].strftime('%Y-%m-%d')} -> "
                      f"{trade['exit_time'].strftime('%Y-%m-%d')} | "
                      f"${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f} | "
                      f"{trade['pnl_pct']:.2f}%")


if __name__ == "__main__":
    main()
