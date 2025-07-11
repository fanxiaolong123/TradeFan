"""
多策略评估系统
支持多个策略在不同币种/周期下的对比分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import os
from datetime import datetime, timedelta
import concurrent.futures
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# 导入策略和模块
from strategies import get_strategy, list_strategies
from modules.data_module import DataModule
from modules.utils import ConfigLoader
from modules.log_module import LogModule
from backtest_visualizer import BacktestVisualizer

class MultiStrategyEvaluator:
    """多策略评估器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化评估器"""
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config
        self.logger = LogModule(self.config)
        self.data_module = DataModule(self.config)
        self.visualizer = BacktestVisualizer()
        
        # 评估结果存储
        self.results = {}
        
    def run_multi_backtest(self, 
                          strategies: List[str], 
                          symbols: List[str], 
                          timeframe: str = '1h',
                          start_date: str = None,
                          end_date: str = None,
                          initial_capital: float = 10000,
                          parallel: bool = True) -> Dict[str, Dict]:
        """
        运行多策略回测
        
        Args:
            strategies: 策略名称列表
            symbols: 交易对列表
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            parallel: 是否并行执行
            
        Returns:
            回测结果字典
        """
        print(f"🚀 开始多策略回测评估")
        print(f"策略数量: {len(strategies)}")
        print(f"交易对数量: {len(symbols)}")
        print(f"总组合数: {len(strategies) * len(symbols)}")
        print("=" * 60)
        
        # 生成所有组合
        combinations = list(product(strategies, symbols))
        
        if parallel and len(combinations) > 1:
            # 并行执行
            results = self._run_parallel_backtest(
                combinations, timeframe, start_date, end_date, initial_capital
            )
        else:
            # 串行执行
            results = self._run_sequential_backtest(
                combinations, timeframe, start_date, end_date, initial_capital
            )
        
        self.results = results
        return results
    
    def _run_parallel_backtest(self, combinations: List[Tuple], 
                              timeframe: str, start_date: str, end_date: str,
                              initial_capital: float) -> Dict:
        """并行执行回测"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有任务
            future_to_combo = {
                executor.submit(
                    self._single_backtest, 
                    strategy_name, symbol, timeframe, 
                    start_date, end_date, initial_capital
                ): (strategy_name, symbol)
                for strategy_name, symbol in combinations
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_combo):
                strategy_name, symbol = future_to_combo[future]
                try:
                    result = future.result()
                    key = f"{strategy_name}_{symbol.replace('/', '_')}"
                    results[key] = result
                    
                    if result:
                        print(f"✅ {strategy_name} - {symbol}: "
                              f"收益率 {result.get('total_return', 0):.2%}")
                    else:
                        print(f"❌ {strategy_name} - {symbol}: 回测失败")
                        
                except Exception as e:
                    print(f"❌ {strategy_name} - {symbol}: 执行异常 - {e}")
        
        return results
    
    def _run_sequential_backtest(self, combinations: List[Tuple],
                                timeframe: str, start_date: str, end_date: str,
                                initial_capital: float) -> Dict:
        """串行执行回测"""
        results = {}
        
        for i, (strategy_name, symbol) in enumerate(combinations, 1):
            print(f"[{i}/{len(combinations)}] 回测 {strategy_name} - {symbol}")
            
            result = self._single_backtest(
                strategy_name, symbol, timeframe, 
                start_date, end_date, initial_capital
            )
            
            key = f"{strategy_name}_{symbol.replace('/', '_')}"
            results[key] = result
            
            if result:
                print(f"✅ 完成: 收益率 {result.get('total_return', 0):.2%}")
            else:
                print(f"❌ 失败")
        
        return results
    
    def _single_backtest(self, strategy_name: str, symbol: str, 
                        timeframe: str, start_date: str, end_date: str,
                        initial_capital: float) -> Optional[Dict]:
        """单个策略回测"""
        try:
            # 获取数据
            data = self._get_backtest_data(symbol, timeframe, start_date, end_date)
            if data.empty:
                return None
            
            # 创建策略实例
            strategy_config = self._get_strategy_config(strategy_name, symbol)
            strategy = get_strategy(strategy_name, **strategy_config)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 执行回测
            backtest_result = self._execute_backtest(
                signals, strategy, symbol, initial_capital
            )
            
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"回测失败 {strategy_name}-{symbol}: {e}")
            return None
    
    def _get_backtest_data(self, symbol: str, timeframe: str, 
                          start_date: str, end_date: str) -> pd.DataFrame:
        """获取回测数据"""
        try:
            # 尝试从数据模块获取数据
            data = self.data_module.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
            
            if data.empty:
                # 生成模拟数据作为备选
                data = self._generate_sample_data(symbol, 1000)
            
            return data
            
        except Exception as e:
            self.logger.warning(f"获取数据失败 {symbol}: {e}, 使用模拟数据")
            return self._generate_sample_data(symbol, 1000)
    
    def _generate_sample_data(self, symbol: str, periods: int) -> pd.DataFrame:
        """生成模拟数据"""
        np.random.seed(42)
        
        # 根据币种设置基础价格
        base_prices = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
            'BNB/USDT': 300,
            'SOL/USDT': 100
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # 生成价格序列
        returns = np.random.normal(0.0001, 0.02, periods)  # 日收益率
        prices = base_price * np.exp(np.cumsum(returns))
        
        # 生成OHLCV数据
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else price
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': pd.Timestamp.now() - pd.Timedelta(hours=periods-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _get_strategy_config(self, strategy_name: str, symbol: str) -> Dict:
        """获取策略配置"""
        # 从配置文件中获取策略参数
        symbols_config = self.config.get('symbols', [])
        
        for symbol_config in symbols_config:
            if symbol_config.get('symbol') == symbol:
                return symbol_config.get('strategy_params', {})
        
        # 返回默认配置
        strategy = get_strategy(strategy_name)
        return strategy.get_default_params()
    
    def _execute_backtest(self, signals: pd.DataFrame, strategy, 
                         symbol: str, initial_capital: float) -> Dict:
        """执行回测逻辑"""
        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = []
        
        commission = 0.001  # 0.1% 手续费
        
        for i, row in signals.iterrows():
            current_price = row['close']
            signal = row['signal']
            
            # 计算当前权益
            current_equity = capital
            if position > 0:
                current_equity += position * current_price
            
            equity_curve.append({
                'timestamp': i,
                'equity': current_equity,
                'position': position,
                'price': current_price
            })
            
            # 处理交易信号
            if signal == 1 and position == 0:  # 买入
                # 使用95%资金买入
                buy_amount = capital * 0.95 / current_price
                position = buy_amount
                entry_price = current_price
                cost = position * current_price * (1 + commission)
                capital -= cost
                
                trades.append({
                    'timestamp': i,
                    'type': 'buy',
                    'price': current_price,
                    'amount': position,
                    'cost': cost
                })
                
            elif signal == -1 and position > 0:  # 卖出
                # 卖出所有持仓
                sell_value = position * current_price * (1 - commission)
                pnl = sell_value - (position * entry_price)
                pnl_pct = pnl / (position * entry_price)
                
                capital += sell_value
                
                trades.append({
                    'timestamp': i,
                    'type': 'sell',
                    'price': current_price,
                    'amount': position,
                    'value': sell_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                position = 0
                entry_price = 0
        
        # 计算最终权益
        final_equity = capital
        if position > 0:
            final_equity += position * signals.iloc[-1]['close']
        
        # 计算性能指标
        metrics = self._calculate_performance_metrics(
            equity_curve, trades, initial_capital, final_equity
        )
        
        return {
            'strategy_name': strategy.name,
            'symbol': symbol,
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'signals': signals,
            'trades': trades,
            'equity_curve': pd.DataFrame(equity_curve),
            **metrics
        }
    
    def _calculate_performance_metrics(self, equity_curve: List, trades: List,
                                     initial_capital: float, final_equity: float) -> Dict:
        """计算性能指标"""
        if not equity_curve:
            return {}
        
        equity_df = pd.DataFrame(equity_curve)
        
        # 基础指标
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 交易统计
        sell_trades = [t for t in trades if t.get('type') == 'sell']
        total_trades = len(sell_trades)
        
        if total_trades > 0:
            winning_trades = len([t for t in sell_trades if t.get('pnl', 0) > 0])
            win_rate = winning_trades / total_trades
            
            pnl_list = [t.get('pnl', 0) for t in sell_trades]
            avg_win = np.mean([p for p in pnl_list if p > 0]) if winning_trades > 0 else 0
            avg_loss = np.mean([p for p in pnl_list if p < 0]) if (total_trades - winning_trades) > 0 else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        else:
            winning_trades = 0
            win_rate = 0
            profit_factor = 0
        
        # 最大回撤
        peak = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - peak) / peak
        max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0
        
        # 夏普比率 (简化计算)
        if len(equity_df) > 1:
            returns = equity_df['equity'].pct_change().dropna()
            if len(returns) > 0 and returns.std() != 0:
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)  # 年化
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio
        }
    
    def generate_comparison_report(self, save_dir: str = "results") -> pd.DataFrame:
        """生成对比报告"""
        if not self.results:
            print("没有回测结果可生成报告")
            return pd.DataFrame()
        
        print("📊 生成策略对比报告...")
        
        # 创建结果目录
        os.makedirs(save_dir, exist_ok=True)
        
        # 整理数据
        report_data = []
        for key, result in self.results.items():
            if result:
                strategy_name, symbol = key.split('_', 1)
                symbol = symbol.replace('_', '/')
                
                report_data.append({
                    '策略': strategy_name,
                    '交易对': symbol,
                    '总收益率': f"{result.get('total_return', 0):.2%}",
                    '最大回撤': f"{result.get('max_drawdown', 0):.2%}",
                    '夏普比率': f"{result.get('sharpe_ratio', 0):.3f}",
                    '总交易次数': result.get('total_trades', 0),
                    '胜率': f"{result.get('win_rate', 0):.1%}",
                    '盈亏比': f"{result.get('profit_factor', 0):.2f}",
                    '最终权益': f"{result.get('final_equity', 0):.2f}"
                })
        
        # 创建DataFrame
        report_df = pd.DataFrame(report_data)
        
        if not report_df.empty:
            # 保存CSV报告
            csv_path = os.path.join(save_dir, f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            report_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"📄 CSV报告已保存: {csv_path}")
            
            # 生成可视化对比图
            chart_path = os.path.join(save_dir, f"strategy_comparison_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self._create_comparison_visualization(report_df, chart_path)
            
            # 打印汇总统计
            self._print_summary_statistics(report_df)
        
        return report_df
    
    def _create_comparison_visualization(self, report_df: pd.DataFrame, save_path: str):
        """创建对比可视化图表"""
        try:
            # 准备数据用于可视化
            results_for_viz = {}
            for _, row in report_df.iterrows():
                key = f"{row['策略']}_{row['交易对']}"
                results_for_viz[key] = {
                    'total_return': float(row['总收益率'].strip('%')) / 100,
                    'max_drawdown': float(row['最大回撤'].strip('%')) / 100,
                    'win_rate': float(row['胜率'].strip('%')) / 100,
                    'sharpe_ratio': float(row['夏普比率'])
                }
            
            self.visualizer.create_strategy_comparison_chart(results_for_viz, save_path)
            
        except Exception as e:
            print(f"⚠️ 生成对比图表失败: {e}")
    
    def _print_summary_statistics(self, report_df: pd.DataFrame):
        """打印汇总统计"""
        print("\n" + "="*80)
        print("📈 策略评估汇总统计")
        print("="*80)
        
        # 按策略分组统计
        print("\n🏆 按策略排名 (按平均收益率):")
        strategy_stats = report_df.groupby('策略').agg({
            '总收益率': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '最大回撤': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '胜率': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '夏普比率': lambda x: np.mean([float(v) for v in x])
        }).round(2)
        
        strategy_stats = strategy_stats.sort_values('总收益率', ascending=False)
        print(strategy_stats)
        
        # 按交易对分组统计
        print("\n💰 按交易对排名 (按平均收益率):")
        symbol_stats = report_df.groupby('交易对').agg({
            '总收益率': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '最大回撤': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '胜率': lambda x: np.mean([float(v.strip('%')) for v in x]),
            '夏普比率': lambda x: np.mean([float(v) for v in x])
        }).round(2)
        
        symbol_stats = symbol_stats.sort_values('总收益率', ascending=False)
        print(symbol_stats)
        
        # 最佳组合
        print("\n🥇 最佳策略组合:")
        best_return = report_df.loc[report_df['总收益率'].str.replace('%', '').astype(float).idxmax()]
        best_sharpe = report_df.loc[report_df['夏普比率'].astype(float).idxmax()]
        best_winrate = report_df.loc[report_df['胜率'].str.replace('%', '').astype(float).idxmax()]
        
        print(f"最高收益率: {best_return['策略']} - {best_return['交易对']} ({best_return['总收益率']})")
        print(f"最高夏普比率: {best_sharpe['策略']} - {best_sharpe['交易对']} ({best_sharpe['夏普比率']})")
        print(f"最高胜率: {best_winrate['策略']} - {best_winrate['交易对']} ({best_winrate['胜率']})")
        
        print("\n" + "="*80)
    
    def get_best_strategies(self, top_n: int = 3) -> List[Dict]:
        """获取最佳策略组合"""
        if not self.results:
            return []
        
        # 计算综合评分
        scored_results = []
        for key, result in self.results.items():
            if result:
                # 综合评分 = 收益率权重 + 夏普比率权重 - 回撤惩罚
                score = (
                    result.get('total_return', 0) * 0.4 +
                    result.get('sharpe_ratio', 0) * 0.3 +
                    result.get('win_rate', 0) * 0.2 -
                    result.get('max_drawdown', 0) * 0.1
                )
                
                scored_results.append({
                    'key': key,
                    'score': score,
                    'result': result
                })
        
        # 按评分排序
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_results[:top_n]

# 使用示例
if __name__ == "__main__":
    # 创建评估器
    evaluator = MultiStrategyEvaluator()
    
    # 运行多策略回测
    strategies = ['trend_ma_breakout', 'donchian_rsi_adx', 'reversal_bollinger']
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    results = evaluator.run_multi_backtest(
        strategies=strategies,
        symbols=symbols,
        timeframe='1h',
        initial_capital=10000
    )
    
    # 生成对比报告
    report = evaluator.generate_comparison_report()
    
    # 获取最佳策略
    best_strategies = evaluator.get_best_strategies(top_n=3)
    print("\n🏆 最佳策略组合:")
    for i, item in enumerate(best_strategies, 1):
        print(f"{i}. {item['key']} - 评分: {item['score']:.3f}")
