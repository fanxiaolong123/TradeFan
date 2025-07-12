"""
TradeFan 多策略回测管理器
支持多个策略在多个交易对上同时回测和优化
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from .backtest_module import BacktestEngine
from .professional_backtest_analyzer import BacktestAnalyzer
from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, MARKET_SPECIFIC_CONFIGS


class MultiStrategyBacktester:
    """多策略回测管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 回测配置
        self.initial_capital = self.config.get('initial_capital', 10000)
        self.commission = self.config.get('commission', 0.001)
        self.slippage = self.config.get('slippage', 0.0005)
        
        # 支持的策略
        self.strategies = {
            'scalping': ScalpingStrategy,
            'trend_following': TrendFollowingStrategy
        }
        
        # 支持的交易对
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT',
            'PEPE/USDT', 'DOGE/USDT', 'WLD/USDT'
        ]
        
        # 回测结果存储
        self.results = {}
        self.best_parameters = {}
        
        # 创建结果目录
        self.results_dir = "results/multi_strategy_backtest"
        os.makedirs(self.results_dir, exist_ok=True)
    
    async def run_comprehensive_backtest(self, 
                                       start_date: str = "2024-01-01",
                                       end_date: str = None,
                                       timeframes: List[str] = None) -> Dict:
        """运行全面的多策略回测"""
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if timeframes is None:
            timeframes = ['5m', '15m', '30m', '1h']
        
        self.logger.info(f"🚀 Starting comprehensive multi-strategy backtest")
        self.logger.info(f"📅 Period: {start_date} to {end_date}")
        self.logger.info(f"📊 Symbols: {self.symbols}")
        self.logger.info(f"⏰ Timeframes: {timeframes}")
        
        all_results = {}
        
        # 1. 短线策略回测
        self.logger.info("📈 Running Scalping Strategy Backtest...")
        scalping_results = await self._backtest_scalping_strategy(
            start_date, end_date, timeframes
        )
        all_results['scalping'] = scalping_results
        
        # 2. 趋势跟踪策略回测
        self.logger.info("📊 Running Trend Following Strategy Backtest...")
        trend_results = await self._backtest_trend_strategy(
            start_date, end_date, timeframes
        )
        all_results['trend_following'] = trend_results
        
        # 3. 生成综合报告
        self.logger.info("📋 Generating comprehensive report...")
        comprehensive_report = self._generate_comprehensive_report(all_results)
        
        # 4. 保存结果
        await self._save_results(all_results, comprehensive_report)
        
        self.logger.info("✅ Comprehensive backtest completed!")
        return {
            'results': all_results,
            'report': comprehensive_report,
            'best_parameters': self.best_parameters
        }
    
    async def _backtest_scalping_strategy(self, start_date: str, end_date: str, 
                                        timeframes: List[str]) -> Dict:
        """回测短线策略"""
        scalping_results = {}
        
        # 短线策略的基础配置
        base_config = {
            'ema_fast': 8,
            'ema_medium': 21,
            'ema_slow': 55,
            'bb_period': 20,
            'bb_std': 2.0,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'signal_threshold': 0.6,
            'max_risk_per_trade': 0.01,
            'stop_loss': 0.02,
            'take_profit': 0.04
        }
        
        for symbol in self.symbols:
            self.logger.info(f"  📊 Backtesting {symbol} with Scalping Strategy...")
            
            symbol_results = {}
            
            for timeframe in timeframes:
                try:
                    # 生成测试数据
                    df = self._generate_market_data(symbol, start_date, end_date, timeframe)
                    
                    # 创建策略实例
                    strategy = ScalpingStrategy(base_config)
                    
                    # 运行回测
                    result = await self._run_single_backtest(
                        strategy, df, symbol, timeframe
                    )
                    
                    symbol_results[timeframe] = result
                    
                    self.logger.info(f"    ✅ {symbol} {timeframe}: "
                                   f"Return: {result['total_return']:.2%}, "
                                   f"Sharpe: {result['sharpe_ratio']:.2f}")
                    
                except Exception as e:
                    self.logger.error(f"    ❌ Error backtesting {symbol} {timeframe}: {e}")
                    symbol_results[timeframe] = None
            
            scalping_results[symbol] = symbol_results
        
        return scalping_results
    
    async def _backtest_trend_strategy(self, start_date: str, end_date: str, 
                                     timeframes: List[str]) -> Dict:
        """回测趋势跟踪策略"""
        trend_results = {}
        
        for symbol in self.symbols:
            self.logger.info(f"  📈 Backtesting {symbol} with Trend Following Strategy...")
            
            # 获取该交易对的优化配置
            config = MARKET_SPECIFIC_CONFIGS.get(symbol, MARKET_SPECIFIC_CONFIGS['BTC/USDT'])
            
            symbol_results = {}
            
            for timeframe in timeframes:
                try:
                    # 生成测试数据
                    df = self._generate_market_data(symbol, start_date, end_date, timeframe)
                    
                    # 创建策略实例
                    strategy = TrendFollowingStrategy(config)
                    
                    # 运行回测
                    result = await self._run_single_backtest(
                        strategy, df, symbol, timeframe
                    )
                    
                    symbol_results[timeframe] = result
                    
                    self.logger.info(f"    ✅ {symbol} {timeframe}: "
                                   f"Return: {result['total_return']:.2%}, "
                                   f"Sharpe: {result['sharpe_ratio']:.2f}")
                    
                except Exception as e:
                    self.logger.error(f"    ❌ Error backtesting {symbol} {timeframe}: {e}")
                    symbol_results[timeframe] = None
            
            trend_results[symbol] = symbol_results
        
        return trend_results
    
    async def _run_single_backtest(self, strategy, df: pd.DataFrame, 
                                 symbol: str, timeframe: str) -> Dict:
        """运行单个策略回测"""
        try:
            # 计算指标
            df = strategy.calculate_indicators(df)
            
            # 生成信号
            signals = strategy.generate_signals(df)
            df['signal'] = signals
            
            # 执行回测
            backtest_result = self._execute_backtest(df, strategy)
            
            # 计算性能指标
            performance_metrics = self._calculate_performance_metrics(
                backtest_result, df, symbol, timeframe
            )
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"Error in single backtest: {e}")
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'error': str(e)
            }
    
    def _execute_backtest(self, df: pd.DataFrame, strategy) -> Dict:
        """执行回测逻辑"""
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = [capital]
        
        for i in range(1, len(df)):
            current_price = df['close'].iloc[i]
            signal = df['signal'].iloc[i]
            prev_signal = df['signal'].iloc[i-1]
            
            # 买入信号
            if signal == 'BUY' and prev_signal != 'BUY' and position <= 0:
                if position < 0:  # 平空仓
                    pnl = position * (df['close'].iloc[i-1] - current_price)
                    capital += pnl
                    trades.append({
                        'type': 'COVER',
                        'price': current_price,
                        'quantity': abs(position),
                        'pnl': pnl,
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
                    })
                
                # 开多仓
                position = (capital * 0.95) / current_price  # 95%资金利用率
                capital *= 0.05  # 保留5%现金
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'quantity': position,
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
                })
            
            # 卖出信号
            elif signal == 'SELL' and prev_signal != 'SELL' and position >= 0:
                if position > 0:  # 平多仓
                    pnl = position * (current_price - df['close'].iloc[i-1])
                    capital += pnl
                    trades.append({
                        'type': 'SELL',
                        'price': current_price,
                        'quantity': position,
                        'pnl': pnl,
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
                    })
                
                # 开空仓 (如果策略支持)
                if hasattr(strategy, 'enable_short') and strategy.enable_short:
                    position = -(capital * 0.95) / current_price
                    capital *= 0.05
                    trades.append({
                        'type': 'SHORT',
                        'price': current_price,
                        'quantity': abs(position),
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else i
                    })
                else:
                    position = 0
            
            # 计算当前权益
            if position > 0:
                current_equity = capital + (position * current_price)
            elif position < 0:
                current_equity = capital - (abs(position) * current_price)
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # 最终平仓
        final_price = df['close'].iloc[-1]
        if position != 0:
            if position > 0:
                final_pnl = position * final_price
            else:
                final_pnl = -abs(position) * final_price
            capital += final_pnl
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    def _calculate_performance_metrics(self, backtest_result: Dict, df: pd.DataFrame,
                                     symbol: str, timeframe: str) -> Dict:
        """计算性能指标"""
        try:
            initial_capital = backtest_result['initial_capital']
            final_capital = backtest_result['final_capital']
            trades = backtest_result['trades']
            equity_curve = backtest_result['equity_curve']
            
            # 基础收益指标
            total_return = (final_capital - initial_capital) / initial_capital
            
            # 交易统计
            profitable_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
            
            total_trades = len([t for t in trades if 'pnl' in t])
            win_rate = len(profitable_trades) / max(total_trades, 1)
            
            # 平均盈亏
            avg_profit = np.mean([t['pnl'] for t in profitable_trades]) if profitable_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
            
            # 最大回撤
            peak = initial_capital
            max_drawdown = 0
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            # 夏普比率 (简化计算)
            if len(equity_curve) > 1:
                returns = np.diff(equity_curve) / equity_curve[:-1]
                sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-6) * np.sqrt(252)
            else:
                sharpe_ratio = 0
            
            # 年化收益率
            days = len(df) / (24 * 60 / self._get_timeframe_minutes(timeframe))
            annual_return = (1 + total_return) ** (365 / max(days, 1)) - 1
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'total_return': total_return,
                'annual_return': annual_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_trades': total_trades,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'final_capital': final_capital,
                'equity_curve': equity_curve[-100:],  # 保存最后100个点
                'trade_summary': {
                    'profitable_trades': len(profitable_trades),
                    'losing_trades': len(losing_trades),
                    'total_pnl': sum([t.get('pnl', 0) for t in trades])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'error': str(e)
            }
    
    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """获取时间框架的分钟数"""
        timeframe_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        return timeframe_map.get(timeframe, 5)
    
    def _generate_market_data(self, symbol: str, start_date: str, end_date: str, 
                            timeframe: str) -> pd.DataFrame:
        """生成模拟市场数据"""
        try:
            # 计算数据点数量
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            total_minutes = int((end_dt - start_dt).total_seconds() / 60)
            
            timeframe_minutes = self._get_timeframe_minutes(timeframe)
            num_points = total_minutes // timeframe_minutes
            
            # 生成时间序列
            dates = pd.date_range(start=start_dt, periods=num_points, 
                                freq=f'{timeframe_minutes}min')
            
            # 设置随机种子以获得一致的结果
            np.random.seed(hash(symbol) % 2**32)
            
            # 根据不同币种设置不同的价格基础
            base_prices = {
                'BTC/USDT': 45000,
                'ETH/USDT': 3000,
                'BNB/USDT': 300,
                'SOL/USDT': 100,
                'PEPE/USDT': 0.000001,
                'DOGE/USDT': 0.1,
                'WLD/USDT': 5.0
            }
            
            base_price = base_prices.get(symbol, 1000)
            
            # 生成价格走势 (带趋势性)
            trend_strength = np.random.uniform(0.0001, 0.0005)  # 轻微上涨趋势
            volatility = np.random.uniform(0.015, 0.025)  # 波动率
            
            returns = np.random.normal(trend_strength, volatility, num_points)
            
            # 添加一些趋势性和周期性
            trend_component = np.sin(np.arange(num_points) * 2 * np.pi / 100) * 0.01
            returns += trend_component
            
            # 计算价格
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # 生成OHLCV数据
            data = []
            for i, (date, close) in enumerate(zip(dates, prices)):
                volatility_factor = abs(np.random.normal(0, 0.01))
                high = close * (1 + volatility_factor)
                low = close * (1 - volatility_factor)
                open_price = close * (1 + np.random.normal(0, 0.005))
                
                # 确保OHLC逻辑正确
                high = max(high, open_price, close)
                low = min(low, open_price, close)
                
                volume = np.random.uniform(1000, 10000)
                
                data.append({
                    'timestamp': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': close,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            self.logger.debug(f"Generated {len(df)} data points for {symbol} {timeframe}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generating market data for {symbol}: {e}")
            # 返回最小数据集
            return pd.DataFrame({
                'timestamp': [datetime.now()],
                'open': [base_prices.get(symbol, 1000)],
                'high': [base_prices.get(symbol, 1000)],
                'low': [base_prices.get(symbol, 1000)],
                'close': [base_prices.get(symbol, 1000)],
                'volume': [1000]
            })
    
    def _generate_comprehensive_report(self, all_results: Dict) -> Dict:
        """生成综合报告"""
        report = {
            'summary': {},
            'best_performers': {},
            'strategy_comparison': {},
            'symbol_analysis': {},
            'recommendations': []
        }
        
        try:
            # 汇总所有结果
            all_performances = []
            
            for strategy_name, strategy_results in all_results.items():
                for symbol, symbol_results in strategy_results.items():
                    for timeframe, result in symbol_results.items():
                        if result and 'total_return' in result:
                            all_performances.append({
                                'strategy': strategy_name,
                                'symbol': symbol,
                                'timeframe': timeframe,
                                **result
                            })
            
            if not all_performances:
                return report
            
            df_results = pd.DataFrame(all_performances)
            
            # 总体统计
            report['summary'] = {
                'total_backtests': len(df_results),
                'avg_return': df_results['total_return'].mean(),
                'avg_sharpe': df_results['sharpe_ratio'].mean(),
                'avg_max_drawdown': df_results['max_drawdown'].mean(),
                'avg_win_rate': df_results['win_rate'].mean(),
                'best_return': df_results['total_return'].max(),
                'worst_return': df_results['total_return'].min()
            }
            
            # 最佳表现者
            best_overall = df_results.loc[df_results['sharpe_ratio'].idxmax()]
            report['best_performers'] = {
                'overall_best': {
                    'strategy': best_overall['strategy'],
                    'symbol': best_overall['symbol'],
                    'timeframe': best_overall['timeframe'],
                    'return': best_overall['total_return'],
                    'sharpe': best_overall['sharpe_ratio']
                }
            }
            
            # 策略对比
            strategy_comparison = df_results.groupby('strategy').agg({
                'total_return': ['mean', 'std', 'max', 'min'],
                'sharpe_ratio': ['mean', 'std', 'max', 'min'],
                'win_rate': 'mean',
                'max_drawdown': 'mean'
            }).round(4)
            
            report['strategy_comparison'] = strategy_comparison.to_dict()
            
            # 交易对分析
            symbol_analysis = df_results.groupby('symbol').agg({
                'total_return': ['mean', 'std'],
                'sharpe_ratio': ['mean', 'std'],
                'win_rate': 'mean'
            }).round(4)
            
            report['symbol_analysis'] = symbol_analysis.to_dict()
            
            # 生成建议
            report['recommendations'] = self._generate_recommendations(df_results)
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {e}")
            report['error'] = str(e)
        
        return report
    
    def _generate_recommendations(self, df_results: pd.DataFrame) -> List[str]:
        """生成交易建议"""
        recommendations = []
        
        try:
            # 找出最佳策略-交易对组合
            best_combinations = df_results.nlargest(5, 'sharpe_ratio')
            
            for _, combo in best_combinations.iterrows():
                recommendations.append(
                    f"推荐: {combo['strategy']} 策略在 {combo['symbol']} "
                    f"{combo['timeframe']} 时间框架表现优异 "
                    f"(收益率: {combo['total_return']:.2%}, 夏普比率: {combo['sharpe_ratio']:.2f})"
                )
            
            # 策略建议
            strategy_performance = df_results.groupby('strategy')['sharpe_ratio'].mean()
            best_strategy = strategy_performance.idxmax()
            recommendations.append(f"整体表现最佳策略: {best_strategy}")
            
            # 交易对建议
            symbol_performance = df_results.groupby('symbol')['total_return'].mean()
            best_symbols = symbol_performance.nlargest(3)
            recommendations.append(f"推荐交易对: {', '.join(best_symbols.index.tolist())}")
            
        except Exception as e:
            recommendations.append(f"生成建议时出错: {e}")
        
        return recommendations
    
    async def _save_results(self, all_results: Dict, report: Dict):
        """保存回测结果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存详细结果
            results_file = f"{self.results_dir}/backtest_results_{timestamp}.json"
            with open(results_file, 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            
            # 保存报告
            report_file = f"{self.results_dir}/backtest_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to: {results_file}")
            self.logger.info(f"Report saved to: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")


# 使用示例
async def main():
    """主函数示例"""
    backtester = MultiStrategyBacktester()
    
    results = await backtester.run_comprehensive_backtest(
        start_date="2024-01-01",
        end_date="2024-06-30",
        timeframes=['5m', '15m', '30m', '1h']
    )
    
    print("🎉 Multi-strategy backtest completed!")
    print(f"📊 Summary: {results['report']['summary']}")


if __name__ == "__main__":
    asyncio.run(main())
