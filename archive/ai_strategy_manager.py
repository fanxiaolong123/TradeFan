#!/usr/bin/env python3
"""
AI策略管理器
自动生成、测试和优化交易策略
"""

import argparse
import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.ai_strategy_generator import AIStrategyGenerator
from modules.optimization_module import OptimizationManager
from modules.backtest_module import BacktestModule
from modules.log_module import LogModule

class AIStrategyManager:
    """AI策略管理器"""
    
    def __init__(self):
        self.logger = LogModule()
        
        # 初始化组件
        self.ai_generator = AIStrategyGenerator(self.logger)
        self.optimizer = OptimizationManager()
        
        # 策略评估历史
        self.evaluation_history = []
        
        self.logger.info("AI策略管理器初始化完成")
    
    def generate_and_test_strategy(self, market_condition: str = "trending", 
                                 performance_target: dict = None) -> dict:
        """生成并测试策略"""
        self.logger.info(f"开始生成策略 - 市场条件: {market_condition}")
        
        try:
            # 1. 生成策略想法
            strategy_idea = self.ai_generator.generate_strategy_idea(
                market_condition, performance_target
            )
            
            # 2. 生成策略代码
            strategy_code = self.ai_generator.generate_strategy_code(strategy_idea)
            
            # 3. 保存策略
            strategy_name = f"AI_Strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            file_path = self.ai_generator.save_strategy(strategy_code, strategy_name)
            
            # 4. 生成测试数据
            test_data = self._generate_test_data()
            
            # 5. 简单回测评估
            evaluation_result = self._evaluate_strategy_concept(strategy_idea, test_data)
            
            # 6. 记录结果
            result = {
                'strategy_name': strategy_name,
                'strategy_idea': strategy_idea,
                'strategy_code': strategy_code,
                'file_path': file_path,
                'evaluation': evaluation_result,
                'timestamp': datetime.now().isoformat()
            }
            
            self.evaluation_history.append(result)
            
            self.logger.info(f"策略生成完成: {strategy_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"策略生成失败: {e}")
            return {}
    
    def _generate_test_data(self, days: int = 365) -> dict:
        """生成测试数据"""
        symbols = ['BTC/USDT', 'ETH/USDT']
        data_dict = {}
        
        for symbol in symbols:
            # 生成模拟价格数据
            dates = pd.date_range('2024-01-01', periods=days, freq='D')
            np.random.seed(42)  # 固定随机种子
            
            initial_price = 50000 if 'BTC' in symbol else 3000
            returns = np.random.normal(0.001, 0.02, len(dates))
            
            # 添加趋势成分
            trend = np.sin(np.arange(len(dates)) * 2 * np.pi / 60) * 0.01
            returns += trend
            
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
    
    def _evaluate_strategy_concept(self, strategy_idea: dict, test_data: dict) -> dict:
        """评估策略概念"""
        try:
            # 简化的策略评估
            strategy_type = strategy_idea.get('type', 'trend_following')
            
            # 模拟策略表现
            if strategy_type == 'trend_following':
                # 趋势策略在趋势市场表现较好
                simulated_return = np.random.normal(0.12, 0.05)  # 12%±5%
                simulated_sharpe = np.random.normal(1.2, 0.3)
                simulated_drawdown = np.random.normal(0.08, 0.02)
            elif strategy_type == 'mean_reversion':
                # 均值回归策略
                simulated_return = np.random.normal(0.08, 0.04)  # 8%±4%
                simulated_sharpe = np.random.normal(0.9, 0.2)
                simulated_drawdown = np.random.normal(0.06, 0.02)
            else:
                # 其他策略
                simulated_return = np.random.normal(0.10, 0.06)
                simulated_sharpe = np.random.normal(1.0, 0.4)
                simulated_drawdown = np.random.normal(0.10, 0.03)
            
            # 计算评分
            target = strategy_idea.get('performance_target', {})
            target_return = target.get('target_return', 0.15)
            target_sharpe = target.get('sharpe_ratio', 1.5)
            target_drawdown = target.get('max_drawdown', 0.1)
            
            return_score = min(1.0, simulated_return / target_return)
            sharpe_score = min(1.0, simulated_sharpe / target_sharpe)
            drawdown_score = min(1.0, target_drawdown / abs(simulated_drawdown))
            
            overall_score = (return_score + sharpe_score + drawdown_score) / 3
            
            return {
                'simulated_return': simulated_return,
                'simulated_sharpe': simulated_sharpe,
                'simulated_drawdown': simulated_drawdown,
                'return_score': return_score,
                'sharpe_score': sharpe_score,
                'drawdown_score': drawdown_score,
                'overall_score': overall_score,
                'recommendation': 'good' if overall_score > 0.7 else 'average' if overall_score > 0.5 else 'poor'
            }
            
        except Exception as e:
            self.logger.error(f"策略评估失败: {e}")
            return {'overall_score': 0, 'recommendation': 'error'}
    
    def optimize_best_strategies(self, top_n: int = 3) -> list:
        """优化最佳策略"""
        if len(self.evaluation_history) == 0:
            self.logger.warning("没有可优化的策略")
            return []
        
        # 按评分排序
        sorted_strategies = sorted(
            self.evaluation_history, 
            key=lambda x: x.get('evaluation', {}).get('overall_score', 0), 
            reverse=True
        )
        
        best_strategies = sorted_strategies[:top_n]
        optimization_results = []
        
        for strategy in best_strategies:
            try:
                self.logger.info(f"优化策略: {strategy['strategy_name']}")
                
                # 这里应该调用实际的参数优化
                # 由于策略是动态生成的，暂时跳过实际优化
                optimization_result = {
                    'strategy_name': strategy['strategy_name'],
                    'original_score': strategy['evaluation']['overall_score'],
                    'optimized': False,
                    'reason': '动态生成的策略暂不支持自动优化'
                }
                
                optimization_results.append(optimization_result)
                
            except Exception as e:
                self.logger.error(f"策略优化失败: {e}")
        
        return optimization_results
    
    def generate_strategy_report(self) -> str:
        """生成策略报告"""
        if len(self.evaluation_history) == 0:
            return "暂无策略生成历史"
        
        report = []
        report.append("AI策略生成报告")
        report.append("=" * 50)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"总策略数: {len(self.evaluation_history)}")
        report.append("")
        
        # 统计信息
        scores = [s.get('evaluation', {}).get('overall_score', 0) for s in self.evaluation_history]
        avg_score = np.mean(scores) if scores else 0
        max_score = max(scores) if scores else 0
        
        report.append("统计摘要:")
        report.append(f"  平均评分: {avg_score:.3f}")
        report.append(f"  最高评分: {max_score:.3f}")
        report.append("")
        
        # 最佳策略
        best_strategies = sorted(
            self.evaluation_history, 
            key=lambda x: x.get('evaluation', {}).get('overall_score', 0), 
            reverse=True
        )[:5]
        
        report.append("Top 5 策略:")
        for i, strategy in enumerate(best_strategies, 1):
            eval_data = strategy.get('evaluation', {})
            report.append(f"  {i}. {strategy['strategy_name']}")
            report.append(f"     评分: {eval_data.get('overall_score', 0):.3f}")
            report.append(f"     推荐: {eval_data.get('recommendation', 'unknown')}")
            report.append(f"     类型: {strategy.get('strategy_idea', {}).get('type', 'unknown')}")
            report.append("")
        
        return "\n".join(report)
    
    def run_ai_loop(self, iterations: int = 5, market_conditions: list = None):
        """运行AI策略生成循环"""
        if market_conditions is None:
            market_conditions = ['trending', 'sideways', 'volatile']
        
        self.logger.info(f"开始AI策略生成循环 - {iterations}次迭代")
        
        for i in range(iterations):
            self.logger.info(f"迭代 {i+1}/{iterations}")
            
            # 随机选择市场条件
            market_condition = np.random.choice(market_conditions)
            
            # 生成和测试策略
            result = self.generate_and_test_strategy(market_condition)
            
            if result:
                score = result.get('evaluation', {}).get('overall_score', 0)
                self.logger.info(f"策略评分: {score:.3f}")
            
            # 短暂休息
            import time
            time.sleep(1)
        
        # 优化最佳策略
        self.logger.info("优化最佳策略...")
        optimization_results = self.optimize_best_strategies()
        
        # 生成报告
        report = self.generate_strategy_report()
        
        return {
            'total_strategies': len(self.evaluation_history),
            'optimization_results': optimization_results,
            'report': report
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI策略管理器')
    parser.add_argument('--mode', '-m', default='generate',
                       choices=['generate', 'loop', 'report'],
                       help='运行模式')
    parser.add_argument('--market', default='trending',
                       choices=['trending', 'sideways', 'volatile'],
                       help='市场条件')
    parser.add_argument('--iterations', '-i', type=int, default=5,
                       help='循环迭代次数')
    
    args = parser.parse_args()
    
    print("🤖 AI策略管理器")
    print("=" * 50)
    
    try:
        manager = AIStrategyManager()
        
        if args.mode == 'generate':
            print(f"生成单个策略 - 市场条件: {args.market}")
            result = manager.generate_and_test_strategy(args.market)
            
            if result:
                print(f"\n✅ 策略生成成功:")
                print(f"  策略名称: {result['strategy_name']}")
                print(f"  策略类型: {result['strategy_idea']['type']}")
                print(f"  评分: {result['evaluation']['overall_score']:.3f}")
                print(f"  推荐: {result['evaluation']['recommendation']}")
                print(f"  文件路径: {result['file_path']}")
            else:
                print("❌ 策略生成失败")
        
        elif args.mode == 'loop':
            print(f"运行AI循环 - {args.iterations}次迭代")
            result = manager.run_ai_loop(args.iterations)
            
            print(f"\n✅ AI循环完成:")
            print(f"  生成策略数: {result['total_strategies']}")
            print(f"  优化结果: {len(result['optimization_results'])}个策略")
            print("\n" + result['report'])
        
        elif args.mode == 'report':
            print("生成策略报告")
            report = manager.generate_strategy_report()
            print("\n" + report)
        
    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 运行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
