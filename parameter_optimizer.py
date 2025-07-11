"""
参数自动优化系统
支持网格搜索和贝叶斯优化
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 导入策略和模块
from strategies import get_strategy
from multi_strategy_evaluator import MultiStrategyEvaluator

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("⚠️ Optuna未安装，将只使用网格搜索。安装命令: pip install optuna")

class ParameterOptimizer:
    """参数优化器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化优化器"""
        self.evaluator = MultiStrategyEvaluator(config_path)
        self.optimization_results = {}
        
    def grid_search_optimization(self, 
                               strategy_name: str,
                               symbol: str,
                               param_ranges: Dict[str, List],
                               timeframe: str = '1h',
                               initial_capital: float = 10000,
                               objective: str = 'sharpe_ratio',
                               max_combinations: int = 1000,
                               parallel: bool = True) -> Dict:
        """
        网格搜索参数优化
        
        Args:
            strategy_name: 策略名称
            symbol: 交易对
            param_ranges: 参数范围字典
            timeframe: 时间周期
            initial_capital: 初始资金
            objective: 优化目标 ('sharpe_ratio', 'total_return', 'profit_factor')
            max_combinations: 最大组合数
            parallel: 是否并行执行
            
        Returns:
            优化结果
        """
        print(f"🔍 开始网格搜索优化")
        print(f"策略: {strategy_name}")
        print(f"交易对: {symbol}")
        print(f"优化目标: {objective}")
        print("=" * 60)
        
        # 生成参数组合
        param_combinations = self._generate_param_combinations(param_ranges, max_combinations)
        print(f"参数组合数量: {len(param_combinations)}")
        
        if len(param_combinations) == 0:
            print("❌ 没有有效的参数组合")
            return {}
        
        # 执行优化
        start_time = time.time()
        
        if parallel and len(param_combinations) > 1:
            results = self._run_parallel_optimization(
                strategy_name, symbol, param_combinations, 
                timeframe, initial_capital, objective
            )
        else:
            results = self._run_sequential_optimization(
                strategy_name, symbol, param_combinations,
                timeframe, initial_capital, objective
            )
        
        end_time = time.time()
        
        # 分析结果
        optimization_result = self._analyze_optimization_results(
            results, param_ranges, objective, end_time - start_time
        )
        
        # 保存结果
        key = f"{strategy_name}_{symbol.replace('/', '_')}_grid"
        self.optimization_results[key] = optimization_result
        
        return optimization_result
    
    def bayesian_optimization(self,
                            strategy_name: str,
                            symbol: str,
                            param_ranges: Dict[str, Tuple],
                            timeframe: str = '1h',
                            initial_capital: float = 10000,
                            objective: str = 'sharpe_ratio',
                            n_trials: int = 100,
                            timeout: int = 3600) -> Dict:
        """
        贝叶斯优化参数搜索
        
        Args:
            strategy_name: 策略名称
            symbol: 交易对
            param_ranges: 参数范围字典 {param: (min, max, step)}
            timeframe: 时间周期
            initial_capital: 初始资金
            objective: 优化目标
            n_trials: 试验次数
            timeout: 超时时间(秒)
            
        Returns:
            优化结果
        """
        if not OPTUNA_AVAILABLE:
            print("❌ Optuna未安装，无法使用贝叶斯优化")
            return {}
        
        print(f"🧠 开始贝叶斯优化")
        print(f"策略: {strategy_name}")
        print(f"交易对: {symbol}")
        print(f"优化目标: {objective}")
        print(f"试验次数: {n_trials}")
        print("=" * 60)
        
        # 创建优化目标函数
        def objective_function(trial):
            # 生成参数
            params = {}
            for param_name, (min_val, max_val, step) in param_ranges.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = trial.suggest_int(param_name, min_val, max_val, step=step)
                else:
                    params[param_name] = trial.suggest_float(param_name, min_val, max_val, step=step)
            
            # 执行单次回测
            result = self._single_backtest_with_params(
                strategy_name, symbol, params, timeframe, initial_capital
            )
            
            if result is None:
                return -999  # 失败时返回很低的分数
            
            # 返回优化目标值
            return result.get(objective, 0)
        
        # 创建研究对象
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42)
        )
        
        # 执行优化
        start_time = time.time()
        study.optimize(objective_function, n_trials=n_trials, timeout=timeout)
        end_time = time.time()
        
        # 分析结果
        optimization_result = self._analyze_bayesian_results(
            study, objective, end_time - start_time
        )
        
        # 保存结果
        key = f"{strategy_name}_{symbol.replace('/', '_')}_bayesian"
        self.optimization_results[key] = optimization_result
        
        return optimization_result
    
    def _generate_param_combinations(self, param_ranges: Dict[str, List], 
                                   max_combinations: int) -> List[Dict]:
        """生成参数组合"""
        # 计算总组合数
        total_combinations = 1
        for values in param_ranges.values():
            total_combinations *= len(values)
        
        if total_combinations > max_combinations:
            print(f"⚠️ 总组合数({total_combinations})超过限制({max_combinations})")
            print("将使用随机采样减少组合数")
            
            # 随机采样
            combinations = []
            np.random.seed(42)
            
            for _ in range(max_combinations):
                combination = {}
                for param_name, values in param_ranges.items():
                    combination[param_name] = np.random.choice(values)
                combinations.append(combination)
            
            return combinations
        else:
            # 生成所有组合
            param_names = list(param_ranges.keys())
            param_values = list(param_ranges.values())
            
            combinations = []
            for combination in itertools.product(*param_values):
                param_dict = dict(zip(param_names, combination))
                combinations.append(param_dict)
            
            return combinations
    
    def _run_parallel_optimization(self, strategy_name: str, symbol: str,
                                 param_combinations: List[Dict],
                                 timeframe: str, initial_capital: float,
                                 objective: str) -> List[Dict]:
        """并行执行优化"""
        results = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有任务
            future_to_params = {
                executor.submit(
                    self._single_backtest_with_params,
                    strategy_name, symbol, params, timeframe, initial_capital
                ): params
                for params in param_combinations
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    if result:
                        result['params'] = params
                        results.append(result)
                    
                    completed += 1
                    if completed % 10 == 0:
                        print(f"已完成: {completed}/{len(param_combinations)}")
                        
                except Exception as e:
                    print(f"⚠️ 参数组合失败 {params}: {e}")
        
        return results
    
    def _run_sequential_optimization(self, strategy_name: str, symbol: str,
                                   param_combinations: List[Dict],
                                   timeframe: str, initial_capital: float,
                                   objective: str) -> List[Dict]:
        """串行执行优化"""
        results = []
        
        for i, params in enumerate(param_combinations, 1):
            print(f"[{i}/{len(param_combinations)}] 测试参数: {params}")
            
            result = self._single_backtest_with_params(
                strategy_name, symbol, params, timeframe, initial_capital
            )
            
            if result:
                result['params'] = params
                results.append(result)
                print(f"✅ {objective}: {result.get(objective, 0):.4f}")
            else:
                print("❌ 回测失败")
        
        return results
    
    def _single_backtest_with_params(self, strategy_name: str, symbol: str,
                                   params: Dict, timeframe: str,
                                   initial_capital: float) -> Optional[Dict]:
        """使用指定参数执行单次回测"""
        try:
            # 获取数据
            data = self.evaluator._get_backtest_data(symbol, timeframe, None, None)
            if data.empty:
                return None
            
            # 创建策略实例
            strategy = get_strategy(strategy_name, **params)
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 执行回测
            result = self.evaluator._execute_backtest(
                signals, strategy, symbol, initial_capital
            )
            
            return result
            
        except Exception as e:
            return None
    
    def _analyze_optimization_results(self, results: List[Dict], 
                                    param_ranges: Dict, objective: str,
                                    elapsed_time: float) -> Dict:
        """分析优化结果"""
        if not results:
            return {'error': '没有有效的优化结果'}
        
        # 按目标值排序
        results.sort(key=lambda x: x.get(objective, -999), reverse=True)
        
        best_result = results[0]
        worst_result = results[-1]
        
        # 计算统计信息
        objective_values = [r.get(objective, 0) for r in results]
        
        analysis = {
            'optimization_type': 'grid_search',
            'objective': objective,
            'total_combinations': len(results),
            'elapsed_time': elapsed_time,
            'best_params': best_result['params'],
            'best_score': best_result.get(objective, 0),
            'best_result': best_result,
            'worst_score': worst_result.get(objective, 0),
            'mean_score': np.mean(objective_values),
            'std_score': np.std(objective_values),
            'all_results': results[:10],  # 保存前10个结果
            'param_sensitivity': self._analyze_param_sensitivity(results, objective)
        }
        
        # 打印结果
        self._print_optimization_summary(analysis)
        
        return analysis
    
    def _analyze_bayesian_results(self, study, objective: str, 
                                elapsed_time: float) -> Dict:
        """分析贝叶斯优化结果"""
        best_trial = study.best_trial
        
        analysis = {
            'optimization_type': 'bayesian',
            'objective': objective,
            'total_trials': len(study.trials),
            'elapsed_time': elapsed_time,
            'best_params': best_trial.params,
            'best_score': best_trial.value,
            'best_trial': best_trial,
            'study': study
        }
        
        # 打印结果
        self._print_optimization_summary(analysis)
        
        return analysis
    
    def _analyze_param_sensitivity(self, results: List[Dict], 
                                 objective: str) -> Dict:
        """分析参数敏感性"""
        if len(results) < 10:
            return {}
        
        # 创建DataFrame便于分析
        data = []
        for result in results:
            row = result['params'].copy()
            row[objective] = result.get(objective, 0)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # 计算相关性
        correlations = {}
        for param in df.columns:
            if param != objective:
                try:
                    corr = df[param].corr(df[objective])
                    if not pd.isna(corr):
                        correlations[param] = corr
                except:
                    pass
        
        return correlations
    
    def _print_optimization_summary(self, analysis: Dict):
        """打印优化结果摘要"""
        print("\n" + "="*60)
        print("🎯 参数优化结果摘要")
        print("="*60)
        
        print(f"优化类型: {analysis['optimization_type']}")
        print(f"优化目标: {analysis['objective']}")
        print(f"总试验次数: {analysis.get('total_combinations', analysis.get('total_trials', 0))}")
        print(f"耗时: {analysis['elapsed_time']:.2f}秒")
        
        print(f"\n🏆 最佳结果:")
        print(f"最佳参数: {analysis['best_params']}")
        print(f"最佳得分: {analysis['best_score']:.4f}")
        
        if 'mean_score' in analysis:
            print(f"\n📊 统计信息:")
            print(f"平均得分: {analysis['mean_score']:.4f}")
            print(f"标准差: {analysis['std_score']:.4f}")
            print(f"最差得分: {analysis['worst_score']:.4f}")
        
        if 'param_sensitivity' in analysis and analysis['param_sensitivity']:
            print(f"\n🔍 参数敏感性分析:")
            for param, corr in sorted(analysis['param_sensitivity'].items(), 
                                    key=lambda x: abs(x[1]), reverse=True):
                print(f"{param}: {corr:.3f}")
        
        print("="*60)
    
    def compare_optimization_methods(self, strategy_name: str, symbol: str,
                                   param_ranges_grid: Dict[str, List],
                                   param_ranges_bayesian: Dict[str, Tuple],
                                   objective: str = 'sharpe_ratio') -> Dict:
        """比较不同优化方法"""
        print("🔬 比较优化方法性能")
        print("="*60)
        
        results = {}
        
        # 网格搜索
        print("1. 执行网格搜索...")
        grid_result = self.grid_search_optimization(
            strategy_name, symbol, param_ranges_grid, 
            objective=objective, max_combinations=100
        )
        results['grid_search'] = grid_result
        
        # 贝叶斯优化
        if OPTUNA_AVAILABLE:
            print("\n2. 执行贝叶斯优化...")
            bayesian_result = self.bayesian_optimization(
                strategy_name, symbol, param_ranges_bayesian,
                objective=objective, n_trials=100
            )
            results['bayesian'] = bayesian_result
        
        # 比较结果
        print("\n" + "="*60)
        print("📈 优化方法对比")
        print("="*60)
        
        for method, result in results.items():
            if result and 'best_score' in result:
                print(f"{method}:")
                print(f"  最佳得分: {result['best_score']:.4f}")
                print(f"  最佳参数: {result['best_params']}")
                print(f"  耗时: {result['elapsed_time']:.2f}秒")
                print()
        
        return results
    
    def save_optimization_results(self, filepath: str):
        """保存优化结果"""
        import json
        
        # 准备可序列化的数据
        serializable_results = {}
        for key, result in self.optimization_results.items():
            serializable_result = {}
            for k, v in result.items():
                if k not in ['study', 'best_trial', 'all_results']:  # 跳过不可序列化的对象
                    try:
                        json.dumps(v)  # 测试是否可序列化
                        serializable_result[k] = v
                    except:
                        serializable_result[k] = str(v)
            
            serializable_results[key] = serializable_result
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 优化结果已保存到: {filepath}")

# 使用示例
if __name__ == "__main__":
    # 创建优化器
    optimizer = ParameterOptimizer()
    
    # 定义参数范围
    param_ranges_grid = {
        'fast_ma': [10, 15, 20, 25],
        'slow_ma': [30, 40, 50, 60],
        'rsi_period': [12, 14, 16],
        'rsi_overbought': [70, 75, 80]
    }
    
    param_ranges_bayesian = {
        'fast_ma': (5, 30, 1),
        'slow_ma': (20, 100, 5),
        'rsi_period': (10, 20, 1),
        'rsi_overbought': (65, 85, 1)
    }
    
    # 执行优化
    result = optimizer.grid_search_optimization(
        strategy_name='trend_ma_breakout',
        symbol='BTC/USDT',
        param_ranges=param_ranges_grid,
        objective='sharpe_ratio',
        max_combinations=50
    )
    
    # 保存结果
    optimizer.save_optimization_results('results/optimization_results.json')
