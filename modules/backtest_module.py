"""
回测模块
负责历史数据回测、性能分析等功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import os

from .utils import DataProcessor, OrderType

class BacktestModule:
    """回测模块"""
    
    def __init__(self, config: Dict, data_module, strategy_manager, 
                 risk_control, execution_module, logger=None):
        self.config = config
        self.data_module = data_module
        self.strategy_manager = strategy_manager
        self.risk_control = risk_control
        self.execution_module = execution_module
        self.logger = logger
        
        # 回测参数
        backtest_config = config.get('backtest', {})
        self.start_date = backtest_config.get('start_date', '2024-01-01')
        self.end_date = backtest_config.get('end_date', '2024-12-31')
        self.initial_capital = config.get('risk_control', {}).get('initial_capital', 10000)
        
        # 回测结果
        self.results = {}
        self.equity_curve = []
        self.trade_log = []
        self.daily_returns = []
        
        if self.logger:
            self.logger.info(f"回测模块初始化完成 - 期间: {self.start_date} 至 {self.end_date}")
    
    def run_backtest(self, symbols: List[str], strategy_name: str = "TrendFollowing") -> Dict:
        """
        运行回测
        
        Args:
            symbols: 交易对列表
            strategy_name: 策略名称
            
        Returns:
            回测结果
        """
        try:
            if self.logger:
                self.logger.info(f"开始回测 - 策略: {strategy_name}, 币种: {symbols}")
            
            # 重置模块状态
            self._reset_modules()
            
            # 获取历史数据
            historical_data = self._load_historical_data(symbols)
            if not historical_data:
                raise Exception("无法加载历史数据")
            
            # 获取策略
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if not strategy:
                raise Exception(f"策略{strategy_name}不存在")
            
            # 执行回测
            self._execute_backtest(historical_data, strategy, symbols)
            
            # 计算回测结果
            results = self._calculate_results()
            
            # 生成报告
            self._generate_report(results)
            
            if self.logger:
                self.logger.info("回测完成")
            
            return results
            
        except Exception as e:
            error_msg = f"回测执行失败: {e}"
            if self.logger:
                self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _load_historical_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """加载历史数据"""
        historical_data = {}
        timeframe = self.config.get('strategy', {}).get('timeframe', '1h')
        
        for symbol in symbols:
            try:
                if self.logger:
                    self.logger.info(f"加载{symbol}历史数据...")
                
                data = self.data_module.get_historical_data(
                    symbol, timeframe, self.start_date, self.end_date
                )
                
                if data.empty:
                    if self.logger:
                        self.logger.warning(f"{symbol}历史数据为空")
                    continue
                
                historical_data[symbol] = data
                
                if self.logger:
                    self.logger.info(f"{symbol}数据加载完成，共{len(data)}条记录")
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"加载{symbol}数据失败: {e}")
                continue
        
        return historical_data
    
    def _execute_backtest(self, historical_data: Dict[str, pd.DataFrame], 
                         strategy, symbols: List[str]):
        """执行回测逻辑"""
        # 获取所有时间点
        all_timestamps = set()
        for data in historical_data.values():
            all_timestamps.update(data.index)
        
        timestamps = sorted(all_timestamps)
        
        if self.logger:
            self.logger.info(f"回测时间点数量: {len(timestamps)}")
        
        # 逐个时间点执行
        for i, timestamp in enumerate(timestamps):
            try:
                # 更新当前时间的数据
                current_data = {}
                current_prices = {}
                
                for symbol in symbols:
                    if symbol in historical_data:
                        data = historical_data[symbol]
                        # 获取到当前时间点的所有历史数据
                        current_data[symbol] = data[data.index <= timestamp]
                        
                        if not current_data[symbol].empty:
                            current_prices[symbol] = current_data[symbol]['close'].iloc[-1]
                
                # 更新持仓的未实现盈亏
                self._update_unrealized_pnl(current_prices)
                
                # 检查止损止盈
                self._check_stop_loss_take_profit(current_prices)
                
                # 生成交易信号
                for symbol in symbols:
                    if symbol not in current_data or len(current_data[symbol]) < 50:
                        continue
                    
                    try:
                        signal, indicators = strategy.get_latest_signal(current_data[symbol])
                        
                        if signal != 0:
                            self._process_signal(symbol, signal, current_prices[symbol], 
                                               indicators, timestamp)
                    
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"处理{symbol}信号失败: {e}")
                        continue
                
                # 记录权益曲线
                portfolio_status = self.risk_control.get_portfolio_status()
                self.equity_curve.append({
                    'timestamp': timestamp,
                    'equity': portfolio_status.get('current_capital', self.initial_capital),
                    'positions': {symbol: self.risk_control.get_position(symbol).size 
                                for symbol in symbols}
                })
                
                # 定期输出进度
                if i % 1000 == 0 and self.logger:
                    progress = (i + 1) / len(timestamps) * 100
                    self.logger.info(f"回测进度: {progress:.1f}% ({timestamp})")
                    
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"处理时间点{timestamp}失败: {e}")
                continue
    
    def _process_signal(self, symbol: str, signal: int, current_price: float, 
                       indicators: Dict, timestamp: pd.Timestamp):
        """处理交易信号"""
        try:
            position = self.risk_control.get_position(symbol)
            
            # 计算信号强度（简化处理）
            signal_strength = 0.5  # 可以根据indicators计算
            
            if signal == 1:  # 买入信号
                if position.is_empty() or position.is_short():
                    # 计算仓位大小
                    position_size = self.risk_control.calculate_position_size(
                        symbol, signal_strength, current_price
                    )
                    
                    if position_size > 0:
                        # 风控检查
                        passed, reason, adjusted_size = self.risk_control.check_position_limit(
                            symbol, position_size, current_price
                        )
                        
                        if passed:
                            # 执行买入
                            order = self.execution_module.simulate_market_order(
                                symbol, OrderType.BUY, adjusted_size, 
                                pd.DataFrame([{'open': current_price}])
                            )
                            
                            if order:
                                # 更新持仓
                                self.risk_control.update_position(
                                    symbol, OrderType.BUY, order.filled_amount, order.filled_price
                                )
                                
                                # 记录交易
                                self._log_trade(order, timestamp, indicators)
                                
                                if self.logger:
                                    self.logger.debug(f"买入执行: {symbol} {order.filled_amount:.6f} @ {order.filled_price:.6f}")
                        else:
                            if self.logger:
                                self.logger.debug(f"买入被风控拒绝: {symbol} - {reason}")
            
            elif signal == -1:  # 卖出信号
                if position.is_empty() or position.is_long():
                    # 如果有多头持仓，先平仓
                    if position.is_long():
                        order = self.execution_module.simulate_market_order(
                            symbol, OrderType.SELL, position.size,
                            pd.DataFrame([{'open': current_price}])
                        )
                        
                        if order:
                            # 更新持仓
                            self.risk_control.update_position(
                                symbol, OrderType.SELL, order.filled_amount, order.filled_price
                            )
                            
                            # 记录交易
                            self._log_trade(order, timestamp, indicators)
                            
                            if self.logger:
                                self.logger.debug(f"平多执行: {symbol} {order.filled_amount:.6f} @ {order.filled_price:.6f}")
                    
                    # 可以在这里添加开空逻辑（如果支持做空）
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"处理{symbol}信号失败: {e}")
    
    def _update_unrealized_pnl(self, current_prices: Dict[str, float]):
        """更新未实现盈亏"""
        for symbol, price in current_prices.items():
            position = self.risk_control.get_position(symbol)
            if not position.is_empty():
                position.update_unrealized_pnl(price)
    
    def _check_stop_loss_take_profit(self, current_prices: Dict[str, float]):
        """检查止损止盈"""
        for symbol, price in current_prices.items():
            stop_orders = self.risk_control.check_stop_loss_take_profit(symbol, price)
            
            for stop_order in stop_orders:
                try:
                    order = self.execution_module.simulate_market_order(
                        stop_order['symbol'], stop_order['side'], stop_order['amount'],
                        pd.DataFrame([{'open': stop_order['price']}])
                    )
                    
                    if order:
                        # 更新持仓
                        self.risk_control.update_position(
                            symbol, stop_order['side'], order.filled_amount, order.filled_price
                        )
                        
                        # 记录交易
                        self._log_trade(order, pd.Timestamp.now(), 
                                      {'reason': stop_order['reason']})
                        
                        if self.logger:
                            self.logger.info(f"止损止盈触发: {symbol} {stop_order['reason']}")
                            
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"执行止损止盈失败: {e}")
    
    def _log_trade(self, order, timestamp: pd.Timestamp, indicators: Dict):
        """记录交易"""
        self.trade_log.append({
            'timestamp': timestamp,
            'symbol': order.symbol,
            'side': order.side,
            'amount': order.filled_amount,
            'price': order.filled_price,
            'commission': order.commission,
            'indicators': indicators.copy()
        })
    
    def _calculate_results(self) -> Dict:
        """计算回测结果"""
        try:
            if not self.equity_curve:
                return {}
            
            # 转换为DataFrame
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df.set_index('timestamp', inplace=True)
            
            # 计算收益率
            returns = equity_df['equity'].pct_change().dropna()
            
            # 基础指标
            total_return = (equity_df['equity'].iloc[-1] - self.initial_capital) / self.initial_capital
            annual_return = (1 + total_return) ** (252 / len(equity_df)) - 1
            
            # 风险指标
            volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
            sharpe_ratio = DataProcessor.calculate_sharpe_ratio(returns) if len(returns) > 1 else 0
            max_drawdown = DataProcessor.calculate_max_drawdown(
                DataProcessor.calculate_cumulative_returns(returns)
            ) if len(returns) > 1 else 0
            
            # 交易统计
            trade_df = pd.DataFrame(self.trade_log) if self.trade_log else pd.DataFrame()
            
            if not trade_df.empty:
                # 计算每笔交易的盈亏
                trade_pnl = []
                for i in range(0, len(trade_df), 2):  # 假设成对交易
                    if i + 1 < len(trade_df):
                        entry = trade_df.iloc[i]
                        exit_trade = trade_df.iloc[i + 1]
                        
                        if entry['side'] == 'buy' and exit_trade['side'] == 'sell':
                            pnl = (exit_trade['price'] - entry['price']) * entry['amount'] - entry['commission'] - exit_trade['commission']
                            trade_pnl.append(pnl)
                
                winning_trades = len([pnl for pnl in trade_pnl if pnl > 0])
                losing_trades = len([pnl for pnl in trade_pnl if pnl < 0])
                total_trades = len(trade_pnl)
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                
                avg_win = np.mean([pnl for pnl in trade_pnl if pnl > 0]) if winning_trades > 0 else 0
                avg_loss = np.mean([pnl for pnl in trade_pnl if pnl < 0]) if losing_trades > 0 else 0
                profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 and losing_trades > 0 else 0
            else:
                total_trades = winning_trades = losing_trades = 0
                win_rate = avg_win = avg_loss = profit_factor = 0
            
            # 组装结果
            results = {
                'total_return': total_return,
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'initial_capital': self.initial_capital,
                'final_capital': equity_df['equity'].iloc[-1],
                'equity_curve': equity_df,
                'trade_log': trade_df,
                'returns': returns
            }
            
            self.results = results
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算回测结果失败: {e}")
            return {}
    
    def _generate_report(self, results: Dict):
        """生成回测报告"""
        try:
            if self.logger:
                self.logger.log_backtest_result(results)
            
            # 保存详细结果
            self._save_results(results)
            
            # 生成图表
            self._plot_results(results)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成回测报告失败: {e}")
    
    def _save_results(self, results: Dict):
        """保存回测结果"""
        try:
            # 创建结果目录
            results_dir = "results"
            os.makedirs(results_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存权益曲线
            if 'equity_curve' in results and not results['equity_curve'].empty:
                equity_file = f"{results_dir}/equity_curve_{timestamp}.csv"
                results['equity_curve'].to_csv(equity_file)
                
                if self.logger:
                    self.logger.info(f"权益曲线已保存: {equity_file}")
            
            # 保存交易记录
            if 'trade_log' in results and not results['trade_log'].empty:
                trade_file = f"{results_dir}/trade_log_{timestamp}.csv"
                results['trade_log'].to_csv(trade_file, index=False)
                
                if self.logger:
                    self.logger.info(f"交易记录已保存: {trade_file}")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存回测结果失败: {e}")
    
    def _plot_results(self, results: Dict):
        """绘制回测结果图表"""
        try:
            if 'equity_curve' not in results or results['equity_curve'].empty:
                return
            
            equity_df = results['equity_curve']
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # 权益曲线
            ax1.plot(equity_df.index, equity_df['equity'], label='权益曲线', linewidth=2)
            ax1.axhline(y=self.initial_capital, color='r', linestyle='--', alpha=0.7, label='初始资金')
            ax1.set_title('回测权益曲线')
            ax1.set_ylabel('资金 (USDT)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 格式化x轴日期
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            
            # 回撤曲线
            if 'returns' in results and len(results['returns']) > 1:
                cumulative_returns = DataProcessor.calculate_cumulative_returns(results['returns'])
                peak = cumulative_returns.expanding().max()
                drawdown = (cumulative_returns - peak) / (1 + peak)
                
                ax2.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red', label='回撤')
                ax2.axhline(y=-results.get('max_drawdown', 0), color='r', linestyle='--', 
                           label=f'最大回撤: {results.get("max_drawdown", 0):.2%}')
                ax2.set_title('回撤曲线')
                ax2.set_ylabel('回撤比例')
                ax2.set_xlabel('时间')
                ax2.legend()
                ax2.grid(True, alpha=0.3)
                
                # 格式化x轴日期
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            
            plt.tight_layout()
            
            # 保存图表
            results_dir = "results"
            os.makedirs(results_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = f"{results_dir}/backtest_chart_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            
            if self.logger:
                self.logger.info(f"回测图表已保存: {chart_file}")
            
            # 显示图表（如果在交互环境中）
            plt.show()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"绘制回测图表失败: {e}")
    
    def _reset_modules(self):
        """重置各模块状态"""
        self.risk_control.reset()
        self.execution_module.reset()
        self.equity_curve = []
        self.trade_log = []
        self.daily_returns = []
    
    def compare_strategies(self, symbols: List[str], strategies: List[str]) -> Dict:
        """比较多个策略的回测结果"""
        comparison_results = {}
        
        for strategy_name in strategies:
            try:
                if self.logger:
                    self.logger.info(f"回测策略: {strategy_name}")
                
                results = self.run_backtest(symbols, strategy_name)
                comparison_results[strategy_name] = results
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"策略{strategy_name}回测失败: {e}")
                comparison_results[strategy_name] = {}
        
        return comparison_results
    
    def optimize_parameters(self, symbol: str, strategy_name: str, 
                          param_ranges: Dict) -> Dict:
        """参数优化（网格搜索）"""
        # 这里可以实现参数优化逻辑
        # 由于篇幅限制，这里只提供框架
        if self.logger:
            self.logger.info(f"参数优化功能待实现: {strategy_name} - {symbol}")
        
        return {}
