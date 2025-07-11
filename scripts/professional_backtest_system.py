#!/usr/bin/env python3
"""
专业回测系统
集成专业分析器和可视化器，提供机构级别的回测报告
"""

import sys
import os
sys.path.append('.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

from modules.professional_backtest_analyzer import ProfessionalBacktestAnalyzer
from modules.professional_visualizer import ProfessionalVisualizer
from modules.real_data_source import RealDataSource
from strategies.trend_ma_breakout import TrendMABreakoutStrategy
from strategies.donchian_rsi_adx import DonchianRSIADXStrategy
from strategies.reversal_bollinger import ReversalBollingerStrategy

class ProfessionalBacktestSystem:
    """专业回测系统"""
    
    def __init__(self):
        self.analyzer = ProfessionalBacktestAnalyzer()
        self.visualizer = ProfessionalVisualizer()
        self.data_source = RealDataSource()
        
        # 策略注册表
        self.strategies = {
            'trend_ma_breakout': TrendMABreakoutStrategy,
            'donchian_rsi_adx': DonchianRSIADXStrategy,
            'reversal_bollinger': ReversalBollingerStrategy
        }
    
    def run_professional_backtest(self, 
                                strategy_name: str,
                                symbol: str = 'BTCUSDT',
                                start_date: str = '2024-01-01',
                                end_date: str = '2024-03-31',
                                initial_capital: float = 100000,
                                **strategy_params) -> Dict:
        """
        运行专业回测
        
        Args:
            strategy_name: 策略名称
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            **strategy_params: 策略参数
        """
        print(f"🚀 启动专业回测系统")
        print(f"策略: {strategy_name}")
        print(f"交易对: {symbol}")
        print(f"时间范围: {start_date} 到 {end_date}")
        print(f"初始资金: ${initial_capital:,.2f}")
        print("=" * 60)
        
        # 1. 获取数据
        print("📊 获取市场数据...")
        try:
            price_data = self.data_source.get_data(
                symbol=symbol,
                timeframe='1d',
                start_date=start_date,
                end_date=end_date,
                source='binance'
            )
            
            # 转换数据格式
            df = price_data.copy()
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            
            print(f"✅ 数据获取成功: {len(df)} 条记录")
            print(f"   价格范围: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
            
        except Exception as e:
            print(f"❌ 数据获取失败: {str(e)}")
            return None
        
        # 2. 初始化策略
        print(f"\n📈 初始化策略: {strategy_name}")
        try:
            if strategy_name not in self.strategies:
                raise ValueError(f"未知策略: {strategy_name}")
            
            strategy_class = self.strategies[strategy_name]
            strategy = strategy_class(**strategy_params)
            
            print(f"✅ 策略初始化成功")
            print(f"   策略参数: {strategy.params}")
            
        except Exception as e:
            print(f"❌ 策略初始化失败: {str(e)}")
            return None
        
        # 3. 计算技术指标
        print(f"\n🔧 计算技术指标...")
        try:
            df_with_indicators = strategy.calculate_indicators(df)
            indicator_count = len(df_with_indicators.columns) - len(df.columns)
            
            print(f"✅ 技术指标计算完成")
            print(f"   新增指标: {indicator_count} 个")
            print(f"   指标列表: {list(df_with_indicators.columns)}")
            
        except Exception as e:
            print(f"❌ 技术指标计算失败: {str(e)}")
            return None
        
        # 4. 生成交易信号
        print(f"\n📡 生成交易信号...")
        try:
            signals = strategy.generate_signals(df_with_indicators)
            buy_signals = len(signals[signals['signal'] == 'buy'])
            sell_signals = len(signals[signals['signal'] == 'sell'])
            
            print(f"✅ 交易信号生成完成")
            print(f"   买入信号: {buy_signals} 个")
            print(f"   卖出信号: {sell_signals} 个")
            
        except Exception as e:
            print(f"❌ 交易信号生成失败: {str(e)}")
            return None
        
        # 5. 执行回测
        print(f"\n🔄 执行回测计算...")
        try:
            equity_curve, trades = self._execute_backtest(
                df_with_indicators, signals, initial_capital
            )
            
            print(f"✅ 回测执行完成")
            print(f"   交易次数: {len(trades)}")
            print(f"   最终权益: ${equity_curve.iloc[-1]:,.2f}")
            
        except Exception as e:
            print(f"❌ 回测执行失败: {str(e)}")
            return None
        
        # 6. 专业分析
        print(f"\n🔍 执行专业分析...")
        try:
            # 获取基准数据 (买入持有策略)
            benchmark = self._calculate_benchmark(df)
            
            # 执行分析
            analysis_results = self.analyzer.analyze_backtest_results(
                equity_curve=equity_curve,
                trades=trades,
                benchmark=benchmark
            )
            
            print(f"✅ 专业分析完成")
            print(f"   分析指标: {len(analysis_results)} 个")
            
        except Exception as e:
            print(f"❌ 专业分析失败: {str(e)}")
            return None
        
        # 7. 生成报告
        print(f"\n📊 生成专业报告...")
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = f"results/professional_backtest_report_{strategy_name}_{symbol}_{timestamp}.png"
            
            # 确保目录存在
            os.makedirs('results', exist_ok=True)
            
            # 创建可视化报告
            fig = self.visualizer.create_comprehensive_report(
                analysis_results=analysis_results,
                price_data=df_with_indicators,
                trades=trades,
                save_path=report_path
            )
            
            # 生成文字摘要
            summary = self.analyzer.generate_performance_summary(analysis_results)
            
            print(f"✅ 专业报告生成完成")
            print(f"   报告路径: {report_path}")
            
        except Exception as e:
            print(f"❌ 报告生成失败: {str(e)}")
            return None
        
        # 8. 输出摘要
        print(f"\n" + "=" * 60)
        print(summary)
        print("=" * 60)
        
        return {
            'analysis_results': analysis_results,
            'equity_curve': equity_curve,
            'trades': trades,
            'price_data': df_with_indicators,
            'report_path': report_path,
            'summary': summary
        }
    
    def _execute_backtest(self, data: pd.DataFrame, signals: pd.DataFrame, 
                         initial_capital: float) -> tuple:
        """执行回测计算"""
        capital = initial_capital
        position = 0
        trades = []
        equity_curve = []
        
        # 合并数据和信号
        combined = data.join(signals[['signal']], how='left')
        combined['signal'] = combined['signal'].fillna('hold')
        
        for i, (date, row) in enumerate(combined.iterrows()):
            current_price = row['close']
            signal = row['signal']
            
            # 执行交易
            if signal == 'buy' and position == 0:
                # 买入
                shares = capital / current_price
                position = shares
                capital = 0
                
                trades.append({
                    'entry_time': date,
                    'entry_price': current_price,
                    'side': 'buy',
                    'shares': shares,
                    'pnl': 0
                })
                
            elif signal == 'sell' and position > 0:
                # 卖出
                capital = position * current_price
                pnl = capital - initial_capital
                
                # 更新最后一笔交易
                if trades:
                    trades[-1].update({
                        'exit_time': date,
                        'exit_price': current_price,
                        'pnl': pnl
                    })
                
                position = 0
            
            # 计算当前权益
            current_equity = capital + (position * current_price if position > 0 else 0)
            equity_curve.append(current_equity)
        
        # 如果最后还有持仓，按最后价格平仓
        if position > 0:
            final_price = combined['close'].iloc[-1]
            capital = position * final_price
            if trades:
                trades[-1].update({
                    'exit_time': combined.index[-1],
                    'exit_price': final_price,
                    'pnl': capital - initial_capital
                })
        
        # 转换为时间序列
        equity_series = pd.Series(equity_curve, index=combined.index)
        trades_df = pd.DataFrame(trades)
        
        return equity_series, trades_df
    
    def _calculate_benchmark(self, data: pd.DataFrame) -> pd.Series:
        """计算基准收益 (买入持有)"""
        initial_price = data['close'].iloc[0]
        benchmark = data['close'] / initial_price
        return benchmark
    
    def compare_strategies(self, strategies: List[str], 
                          symbol: str = 'BTCUSDT',
                          start_date: str = '2024-01-01',
                          end_date: str = '2024-03-31') -> Dict:
        """比较多个策略"""
        print(f"🔄 开始多策略专业对比")
        print(f"策略列表: {strategies}")
        print(f"交易对: {symbol}")
        print("=" * 60)
        
        results = {}
        
        for strategy_name in strategies:
            print(f"\n📊 回测策略: {strategy_name}")
            result = self.run_professional_backtest(
                strategy_name=strategy_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if result:
                results[strategy_name] = result
                print(f"✅ {strategy_name} 回测完成")
            else:
                print(f"❌ {strategy_name} 回测失败")
        
        # 生成对比报告
        if len(results) > 1:
            self._generate_comparison_report(results)
        
        return results
    
    def _generate_comparison_report(self, results: Dict):
        """生成策略对比报告"""
        print(f"\n📊 生成策略对比报告...")
        
        # 提取关键指标
        comparison_data = []
        for strategy_name, result in results.items():
            analysis = result['analysis_results']
            comparison_data.append({
                '策略': strategy_name,
                '总收益率': analysis['total_return'],
                '年化收益率': analysis['annualized_return'],
                '最大回撤': analysis['max_drawdown'],
                '夏普比率': analysis['sharpe_ratio'],
                '索提诺比率': analysis['sortino_ratio'],
                '胜率': analysis['win_rate'],
                '盈亏比': analysis['profit_factor']
            })
        
        # 创建对比表
        comparison_df = pd.DataFrame(comparison_data)
        
        # 保存对比报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        comparison_path = f"results/strategy_comparison_professional_{timestamp}.csv"
        comparison_df.to_csv(comparison_path, index=False)
        
        print(f"✅ 策略对比报告已保存: {comparison_path}")
        print("\n📊 策略对比摘要:")
        print(comparison_df.round(4))


def demo_professional_backtest():
    """专业回测演示"""
    print("🚀 专业回测系统演示")
    print("=" * 60)
    
    # 创建专业回测系统
    backtest_system = ProfessionalBacktestSystem()
    
    # 单策略专业回测
    print("\n1️⃣ 单策略专业回测演示")
    result = backtest_system.run_professional_backtest(
        strategy_name='trend_ma_breakout',
        symbol='BTCUSDT',
        start_date='2024-01-01',
        end_date='2024-03-31',
        initial_capital=100000,
        fast_ma=10,
        slow_ma=30
    )
    
    if result:
        print(f"\n✅ 单策略回测完成!")
        print(f"📊 报告已保存: {result['report_path']}")
    
    # 多策略对比
    print(f"\n2️⃣ 多策略对比演示")
    comparison_results = backtest_system.compare_strategies(
        strategies=['trend_ma_breakout', 'donchian_rsi_adx'],
        symbol='BTCUSDT',
        start_date='2024-01-01',
        end_date='2024-03-31'
    )
    
    print(f"\n🎉 专业回测演示完成!")
    print(f"📁 所有报告已保存到 results/ 目录")
    
    return result, comparison_results


if __name__ == "__main__":
    demo_professional_backtest()
