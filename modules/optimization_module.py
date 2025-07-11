"""
策略参数优化模块
支持网格搜索、贝叶斯优化等多种优化算法
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Callable
from itertools import product
import json
import os
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from dataclasses import dataclass
from .log_module import LogModule
from .backtest_module import BacktestModule
from .utils import DataProcessor

@dataclass
class OptimizationResult:
    """优化结果数据类"""
    params: Dict[str, Any]
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    score: float  # 综合评分

class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, config: Dict, logger: LogModule = None):
        self.config = config
        self.logger = logger or LogModule()
        
        # 优化配置
        self.optimization_config = config.get('optimization', {})
        
        # 结果存储
        self.results = []
        self.best_params = {}
        
        # 多进程配置
        self.max_workers = min(mp.cpu_count(), self.optimization_config.get('max_workers', 4))
        
        self.logger.info(f"参数优化器初始化完成，使用{self.max_workers}个进程")
    
    def define_parameter_space(self, strategy_name: str) -> Dict[str, List]:
        """定义参数搜索空间"""
        if strategy_name == "TrendFollowing":
            return {
                'fast_ma': [5, 10, 15, 20, 25],
                'slow_ma': [30, 40, 50, 60, 70],
                'adx_period': [10, 14, 18, 22],
                'adx_threshold': [20, 25, 30, 35],
                'donchian_period': [15, 20, 25, 30]
            }
        elif strategy_name == "MeanReversion":
            return {
                'rsi_period': [10, 14, 18, 22],
                'rsi_oversold': [20, 25, 30],
                'rsi_overbought': [70, 75, 80],
                'bb_period': [15, 20, 25],
                'bb_std': [1.5, 2.0, 2.5]
            }
        else:
            self.logger.warning(f"未知策略类型: {strategy_name}")
            return {}
    
    def generate_parameter_combinations(self, param_space: Dict[str, List]) -> List[Dict]:
        """生成参数组合"""
        keys = list(param_space.keys())
        values = list(param_space.values())
        
        combinations = []
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            
            # 参数合理性检查
            if self._validate_parameters(param_dict):
                combinations.append(param_dict)
        
        self.logger.info(f"生成了{len(combinations)}个参数组合")
        return combinations
    
    def _validate_parameters(self, params: Dict) -> bool:
        """验证参数合理性"""
        # 趋势策略参数验证
        if 'fast_ma' in params and 'slow_ma' in params:
            if params['fast_ma'] >= params['slow_ma']:
                return False
        
        # RSI参数验证
        if 'rsi_oversold' in params and 'rsi_overbought' in params:
            if params['rsi_oversold'] >= params['rsi_overbought']:
                return False
        
        return True
    
    def calculate_fitness_score(self, metrics: Dict) -> float:
        """计算适应度评分"""
        # 权重配置
        weights = self.optimization_config.get('fitness_weights', {
            'total_return': 0.3,
            'sharpe_ratio': 0.3,
            'max_drawdown': 0.2,
            'win_rate': 0.1,
            'total_trades': 0.1
        })
        
        # 归一化指标
        normalized_return = max(0, min(1, metrics['total_return'] / 100))  # 假设100%为满分
        normalized_sharpe = max(0, min(1, metrics['sharpe_ratio'] / 3))    # 假设3为满分
        normalized_drawdown = max(0, 1 - abs(metrics['max_drawdown']) / 50)  # 50%回撤为0分
        normalized_winrate = metrics['win_rate'] / 100
        normalized_trades = min(1, metrics['total_trades'] / 100)  # 100笔交易为满分
        
        # 计算综合评分
        score = (
            normalized_return * weights['total_return'] +
            normalized_sharpe * weights['sharpe_ratio'] +
            normalized_drawdown * weights['max_drawdown'] +
            normalized_winrate * weights['win_rate'] +
            normalized_trades * weights['total_trades']
        )
        
        return score
    
    def grid_search_optimization(self, strategy_name: str, symbols: List[str], 
                               data_dict: Dict[str, pd.DataFrame]) -> List[OptimizationResult]:
        """网格搜索优化"""
        self.logger.info(f"开始网格搜索优化: {strategy_name}")
        
        # 定义参数空间
        param_space = self.define_parameter_space(strategy_name)
        if not param_space:
            return []
        
        # 生成参数组合
        param_combinations = self.generate_parameter_combinations(param_space)
        
        # 并行回测
        results = self._parallel_backtest(
            strategy_name, symbols, data_dict, param_combinations
        )
        
        # 排序结果
        results.sort(key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"网格搜索完成，最佳评分: {results[0].score:.4f}")
        return results
    
    def bayesian_optimization(self, strategy_name: str, symbols: List[str], 
                            data_dict: Dict[str, pd.DataFrame], n_iterations: int = 50) -> List[OptimizationResult]:
        """贝叶斯优化（简化版）"""
        self.logger.info(f"开始贝叶斯优化: {strategy_name}, 迭代次数: {n_iterations}")
        
        try:
            from skopt import gp_minimize
            from skopt.space import Integer, Real
        except ImportError:
            self.logger.warning("scikit-optimize未安装，使用随机搜索替代")
            return self._random_search_optimization(strategy_name, symbols, data_dict, n_iterations)
        
        # 定义搜索空间
        if strategy_name == "TrendFollowing":
            dimensions = [
                Integer(5, 25, name='fast_ma'),
                Integer(30, 70, name='slow_ma'),
                Integer(10, 22, name='adx_period'),
                Integer(20, 35, name='adx_threshold'),
                Integer(15, 30, name='donchian_period')
            ]
        else:
            self.logger.warning(f"贝叶斯优化暂不支持策略: {strategy_name}")
            return []
        
        # 目标函数
        def objective(params):
            param_dict = {dim.name: val for dim, val in zip(dimensions, params)}
            
            if not self._validate_parameters(param_dict):
                return 1.0  # 返回最差评分
            
            result = self._single_backtest(strategy_name, symbols, data_dict, param_dict)
            return -result.score  # 最小化负评分
        
        # 执行优化
        result = gp_minimize(
            func=objective,
            dimensions=dimensions,
            n_calls=n_iterations,
            random_state=42
        )
        
        # 构建结果
        best_params = {dim.name: val for dim, val in zip(dimensions, result.x)}
        best_result = self._single_backtest(strategy_name, symbols, data_dict, best_params)
        
        self.logger.info(f"贝叶斯优化完成，最佳评分: {best_result.score:.4f}")
        return [best_result]
    
    def _random_search_optimization(self, strategy_name: str, symbols: List[str], 
                                  data_dict: Dict[str, pd.DataFrame], n_samples: int = 50) -> List[OptimizationResult]:
        """随机搜索优化"""
        self.logger.info(f"开始随机搜索优化: {strategy_name}, 样本数: {n_samples}")
        
        param_space = self.define_parameter_space(strategy_name)
        if not param_space:
            return []
        
        # 随机采样参数
        param_combinations = []
        for _ in range(n_samples):
            params = {}
            for key, values in param_space.items():
                params[key] = np.random.choice(values)
            
            if self._validate_parameters(params):
                param_combinations.append(params)
        
        # 并行回测
        results = self._parallel_backtest(
            strategy_name, symbols, data_dict, param_combinations
        )
        
        # 排序结果
        results.sort(key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"随机搜索完成，最佳评分: {results[0].score:.4f}")
        return results
    
    def _parallel_backtest(self, strategy_name: str, symbols: List[str], 
                          data_dict: Dict[str, pd.DataFrame], 
                          param_combinations: List[Dict]) -> List[OptimizationResult]:
        """并行回测"""
        self.logger.info(f"开始并行回测，参数组合数: {len(param_combinations)}")
        
        results = []
        
        # 分批处理以避免内存问题
        batch_size = min(100, len(param_combinations))
        
        for i in range(0, len(param_combinations), batch_size):
            batch = param_combinations[i:i+batch_size]
            
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                futures = {
                    executor.submit(
                        self._single_backtest_worker, 
                        strategy_name, symbols, data_dict, params
                    ): params for params in batch
                }
                
                # 收集结果
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        self.logger.error(f"回测任务失败: {e}")
            
            self.logger.info(f"完成批次 {i//batch_size + 1}/{(len(param_combinations)-1)//batch_size + 1}")
        
        return results
    
    def _single_backtest(self, strategy_name: str, symbols: List[str], 
                        data_dict: Dict[str, pd.DataFrame], params: Dict) -> OptimizationResult:
        """单次回测"""
        try:
            # 创建回测模块
            backtest_config = self.config.get('backtest', {})
            backtest_module = BacktestModule(backtest_config)
            
            # 执行回测
            results = backtest_module.run_backtest(strategy_name, symbols, params, data_dict)
            
            if not results:
                return None
            
            # 计算指标
            portfolio_value = results.get('portfolio_value', [])
            trades = results.get('trades', [])
            
            if len(portfolio_value) == 0:
                return None
            
            # 计算性能指标
            returns = DataProcessor.calculate_returns(pd.Series(portfolio_value))
            total_return = (portfolio_value[-1] / portfolio_value[0] - 1) * 100
            sharpe_ratio = DataProcessor.calculate_sharpe_ratio(returns)
            max_drawdown = abs(DataProcessor.calculate_max_drawdown(pd.Series(portfolio_value))) * 100
            win_rate = DataProcessor.calculate_win_rate(returns) * 100
            total_trades = len(trades)
            
            # 计算综合评分
            metrics = {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': total_trades
            }
            
            score = self.calculate_fitness_score(metrics)
            
            return OptimizationResult(
                params=params,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                score=score
            )
            
        except Exception as e:
            self.logger.error(f"回测执行失败: {e}")
            return None
    
    @staticmethod
    def _single_backtest_worker(strategy_name: str, symbols: List[str], 
                               data_dict: Dict[str, pd.DataFrame], params: Dict) -> OptimizationResult:
        """单次回测工作函数（用于多进程）"""
        try:
            # 在子进程中重新创建必要的对象
            from .backtest_module import BacktestModule
            from .utils import DataProcessor
            
            # 创建回测模块
            backtest_config = {
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'commission': 0.001,
                'initial_capital': 10000
            }
            
            backtest_module = BacktestModule(backtest_config)
            
            # 执行回测
            results = backtest_module.run_backtest(strategy_name, symbols, params, data_dict)
            
            if not results:
                return None
            
            # 计算指标
            portfolio_value = results.get('portfolio_value', [])
            trades = results.get('trades', [])
            
            if len(portfolio_value) == 0:
                return None
            
            # 计算性能指标
            returns = DataProcessor.calculate_returns(pd.Series(portfolio_value))
            total_return = (portfolio_value[-1] / portfolio_value[0] - 1) * 100
            sharpe_ratio = DataProcessor.calculate_sharpe_ratio(returns)
            max_drawdown = abs(DataProcessor.calculate_max_drawdown(pd.Series(portfolio_value))) * 100
            win_rate = DataProcessor.calculate_win_rate(returns) * 100
            total_trades = len(trades)
            
            # 计算综合评分
            metrics = {
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': total_trades
            }
            
            # 简化的评分计算
            normalized_return = max(0, min(1, total_return / 100))
            normalized_sharpe = max(0, min(1, sharpe_ratio / 3))
            normalized_drawdown = max(0, 1 - abs(max_drawdown) / 50)
            normalized_winrate = win_rate / 100
            normalized_trades = min(1, total_trades / 100)
            
            score = (
                normalized_return * 0.3 +
                normalized_sharpe * 0.3 +
                normalized_drawdown * 0.2 +
                normalized_winrate * 0.1 +
                normalized_trades * 0.1
            )
            
            return OptimizationResult(
                params=params,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                score=score
            )
            
        except Exception as e:
            return None
    
    def save_optimization_results(self, results: List[OptimizationResult], 
                                strategy_name: str, method: str):
        """保存优化结果"""
        if not results:
            return
        
        # 创建结果目录
        results_dir = "results/optimization"
        os.makedirs(results_dir, exist_ok=True)
        
        # 转换为DataFrame
        data = []
        for result in results:
            row = result.params.copy()
            row.update({
                'total_return': result.total_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'score': result.score
            })
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 保存CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = f"{results_dir}/{strategy_name}_{method}_{timestamp}.csv"
        df.to_csv(csv_path, index=False)
        
        # 保存最佳参数到配置文件
        best_result = results[0]
        config_path = f"{results_dir}/{strategy_name}_best_params_{timestamp}.json"
        
        best_config = {
            'strategy': strategy_name,
            'optimization_method': method,
            'timestamp': timestamp,
            'best_params': best_result.params,
            'performance': {
                'total_return': best_result.total_return,
                'sharpe_ratio': best_result.sharpe_ratio,
                'max_drawdown': best_result.max_drawdown,
                'win_rate': best_result.win_rate,
                'total_trades': best_result.total_trades,
                'score': best_result.score
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(best_config, f, indent=2)
        
        self.logger.info(f"优化结果已保存:")
        self.logger.info(f"  详细结果: {csv_path}")
        self.logger.info(f"  最佳参数: {config_path}")
    
    def update_config_with_best_params(self, results: List[OptimizationResult], 
                                     strategy_name: str, config_path: str = "config/config.yaml"):
        """更新配置文件中的最佳参数"""
        if not results:
            return
        
        best_params = results[0].params
        
        try:
            import yaml
            
            # 读取现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 更新策略参数
            if 'symbols' in config:
                for symbol_config in config['symbols']:
                    if symbol_config.get('enabled', False):
                        symbol_config['strategy_params'] = best_params
            
            # 备份原配置
            backup_path = f"{config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            # 保存新配置
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"配置文件已更新: {config_path}")
            self.logger.info(f"原配置备份: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"更新配置文件失败: {e}")

class OptimizationManager:
    """优化管理器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        from .utils import ConfigLoader
        
        self.config = ConfigLoader(config_path)
        self.logger = LogModule()
        
        # 初始化优化器
        self.optimizer = ParameterOptimizer(self.config.config, self.logger)
        
        self.logger.info("优化管理器初始化完成")
    
    def run_optimization(self, strategy_name: str = "TrendFollowing", 
                        method: str = "grid_search", **kwargs):
        """运行参数优化"""
        self.logger.info(f"开始参数优化: {strategy_name}, 方法: {method}")
        
        # 获取交易币种
        symbols = [s['symbol'] for s in self.config.get_symbols()]
        
        # 生成模拟数据（实际应该使用历史数据）
        data_dict = self._generate_sample_data(symbols)
        
        # 执行优化
        if method == "grid_search":
            results = self.optimizer.grid_search_optimization(strategy_name, symbols, data_dict)
        elif method == "bayesian":
            n_iterations = kwargs.get('n_iterations', 50)
            results = self.optimizer.bayesian_optimization(strategy_name, symbols, data_dict, n_iterations)
        elif method == "random_search":
            n_samples = kwargs.get('n_samples', 50)
            results = self.optimizer._random_search_optimization(strategy_name, symbols, data_dict, n_samples)
        else:
            self.logger.error(f"未知优化方法: {method}")
            return
        
        if not results:
            self.logger.error("优化失败，无有效结果")
            return
        
        # 保存结果
        self.optimizer.save_optimization_results(results, strategy_name, method)
        
        # 更新配置文件
        if kwargs.get('update_config', True):
            self.optimizer.update_config_with_best_params(results, strategy_name)
        
        # 输出最佳结果
        best = results[0]
        self.logger.info("=" * 60)
        self.logger.info("🏆 参数优化完成！")
        self.logger.info("=" * 60)
        self.logger.info(f"最佳参数: {best.params}")
        self.logger.info(f"总收益率: {best.total_return:.2f}%")
        self.logger.info(f"夏普比率: {best.sharpe_ratio:.4f}")
        self.logger.info(f"最大回撤: {best.max_drawdown:.2f}%")
        self.logger.info(f"胜率: {best.win_rate:.2f}%")
        self.logger.info(f"交易次数: {best.total_trades}")
        self.logger.info(f"综合评分: {best.score:.4f}")
        self.logger.info("=" * 60)
        
        return results
    
    def _generate_sample_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """生成样本数据"""
        data_dict = {}
        
        for symbol in symbols:
            # 生成模拟价格数据
            dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
            np.random.seed(42)  # 固定随机种子
            
            initial_price = 50000 if 'BTC' in symbol else 3000
            returns = np.random.normal(0.001, 0.02, len(dates))
            
            prices = [initial_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = pd.DataFrame({
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.uniform(100, 1000, len(dates))
            }, index=dates)
            
            data_dict[symbol] = data
        
        return data_dict
