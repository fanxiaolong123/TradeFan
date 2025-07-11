#!/usr/bin/env python3
"""
策略参数优化工具
支持多种优化算法和可视化结果
"""

import argparse
import sys
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.optimization_module import OptimizationManager
from modules.log_module import LogModule

def create_optimization_report(results, strategy_name, method, output_dir="results/optimization"):
    """创建优化报告"""
    if not results:
        return
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
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
    
    # 创建可视化报告
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f'{strategy_name} 参数优化结果 - {method.upper()}', fontsize=16, fontweight='bold')
    
    # 1. 评分分布
    axes[0, 0].hist(df['score'], bins=30, alpha=0.7, color='blue', edgecolor='black')
    axes[0, 0].axvline(df['score'].mean(), color='red', linestyle='--', label=f'平均值: {df["score"].mean():.3f}')
    axes[0, 0].set_title('综合评分分布')
    axes[0, 0].set_xlabel('评分')
    axes[0, 0].set_ylabel('频次')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. 收益率 vs 夏普比率
    scatter = axes[0, 1].scatter(df['total_return'], df['sharpe_ratio'], 
                                c=df['score'], cmap='viridis', alpha=0.6)
    axes[0, 1].set_title('收益率 vs 夏普比率')
    axes[0, 1].set_xlabel('总收益率 (%)')
    axes[0, 1].set_ylabel('夏普比率')
    axes[0, 1].grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=axes[0, 1], label='评分')
    
    # 3. 最大回撤 vs 胜率
    scatter2 = axes[0, 2].scatter(df['max_drawdown'], df['win_rate'], 
                                 c=df['score'], cmap='viridis', alpha=0.6)
    axes[0, 2].set_title('最大回撤 vs 胜率')
    axes[0, 2].set_xlabel('最大回撤 (%)')
    axes[0, 2].set_ylabel('胜率 (%)')
    axes[0, 2].grid(True, alpha=0.3)
    plt.colorbar(scatter2, ax=axes[0, 2], label='评分')
    
    # 4. 参数重要性（如果是趋势策略）
    if 'fast_ma' in df.columns and 'slow_ma' in df.columns:
        # 快慢均线参数热力图
        pivot_table = df.pivot_table(values='score', index='fast_ma', columns='slow_ma', aggfunc='mean')
        sns.heatmap(pivot_table, ax=axes[1, 0], cmap='viridis', annot=True, fmt='.3f')
        axes[1, 0].set_title('快慢均线参数热力图')
    else:
        axes[1, 0].text(0.5, 0.5, '参数热力图\n(需要特定参数)', ha='center', va='center', 
                       transform=axes[1, 0].transAxes)
        axes[1, 0].set_title('参数热力图')
    
    # 5. Top 10 参数组合
    top_10 = df.nlargest(10, 'score')
    y_pos = range(len(top_10))
    axes[1, 1].barh(y_pos, top_10['score'], alpha=0.7, color='green')
    axes[1, 1].set_yticks(y_pos)
    axes[1, 1].set_yticklabels([f'#{i+1}' for i in range(len(top_10))])
    axes[1, 1].set_title('Top 10 参数组合评分')
    axes[1, 1].set_xlabel('评分')
    axes[1, 1].grid(True, alpha=0.3)
    
    # 6. 性能指标相关性
    metrics_cols = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'score']
    correlation_matrix = df[metrics_cols].corr()
    sns.heatmap(correlation_matrix, ax=axes[1, 2], annot=True, cmap='coolwarm', center=0)
    axes[1, 2].set_title('性能指标相关性')
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    chart_path = f"{output_dir}/{strategy_name}_{method}_report_{timestamp}.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"📊 优化报告已保存: {chart_path}")
    
    # 显示图表
    plt.show()
    
    # 创建文本报告
    report_path = f"{output_dir}/{strategy_name}_{method}_summary_{timestamp}.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"策略参数优化报告\n")
        f.write(f"=" * 50 + "\n")
        f.write(f"策略名称: {strategy_name}\n")
        f.write(f"优化方法: {method}\n")
        f.write(f"优化时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"参数组合数: {len(df)}\n\n")
        
        f.write(f"最佳参数组合:\n")
        f.write(f"-" * 30 + "\n")
        best = results[0]
        for key, value in best.params.items():
            f.write(f"{key}: {value}\n")
        
        f.write(f"\n性能指标:\n")
        f.write(f"-" * 30 + "\n")
        f.write(f"总收益率: {best.total_return:.2f}%\n")
        f.write(f"夏普比率: {best.sharpe_ratio:.4f}\n")
        f.write(f"最大回撤: {best.max_drawdown:.2f}%\n")
        f.write(f"胜率: {best.win_rate:.2f}%\n")
        f.write(f"交易次数: {best.total_trades}\n")
        f.write(f"综合评分: {best.score:.4f}\n\n")
        
        f.write(f"统计摘要:\n")
        f.write(f"-" * 30 + "\n")
        f.write(f"平均收益率: {df['total_return'].mean():.2f}% (±{df['total_return'].std():.2f}%)\n")
        f.write(f"平均夏普比率: {df['sharpe_ratio'].mean():.4f} (±{df['sharpe_ratio'].std():.4f})\n")
        f.write(f"平均最大回撤: {df['max_drawdown'].mean():.2f}% (±{df['max_drawdown'].std():.2f}%)\n")
        f.write(f"平均胜率: {df['win_rate'].mean():.2f}% (±{df['win_rate'].std():.2f}%)\n")
        f.write(f"平均评分: {df['score'].mean():.4f} (±{df['score'].std():.4f})\n")
    
    print(f"📄 文本报告已保存: {report_path}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='策略参数优化工具')
    parser.add_argument('--strategy', '-s', default='TrendFollowing', 
                       help='策略名称 (默认: TrendFollowing)')
    parser.add_argument('--method', '-m', default='grid_search',
                       choices=['grid_search', 'bayesian', 'random_search'],
                       help='优化方法 (默认: grid_search)')
    parser.add_argument('--iterations', '-i', type=int, default=50,
                       help='贝叶斯优化或随机搜索的迭代次数 (默认: 50)')
    parser.add_argument('--no-update-config', action='store_true',
                       help='不更新配置文件')
    parser.add_argument('--no-report', action='store_true',
                       help='不生成可视化报告')
    parser.add_argument('--config', '-c', default='config/config.yaml',
                       help='配置文件路径 (默认: config/config.yaml)')
    
    args = parser.parse_args()
    
    print("🔧 策略参数优化工具")
    print("=" * 50)
    print(f"策略: {args.strategy}")
    print(f"方法: {args.method}")
    if args.method in ['bayesian', 'random_search']:
        print(f"迭代次数: {args.iterations}")
    print("=" * 50)
    
    try:
        # 创建优化管理器
        optimizer_manager = OptimizationManager(args.config)
        
        # 运行优化
        kwargs = {
            'update_config': not args.no_update_config
        }
        
        if args.method in ['bayesian', 'random_search']:
            if args.method == 'bayesian':
                kwargs['n_iterations'] = args.iterations
            else:
                kwargs['n_samples'] = args.iterations
        
        results = optimizer_manager.run_optimization(
            strategy_name=args.strategy,
            method=args.method,
            **kwargs
        )
        
        if not results:
            print("❌ 优化失败，无有效结果")
            return
        
        # 生成报告
        if not args.no_report:
            print("\n📊 生成优化报告...")
            create_optimization_report(results, args.strategy, args.method)
        
        print("\n✅ 参数优化完成！")
        
        # 显示最佳参数
        best = results[0]
        print(f"\n🏆 最佳参数组合:")
        for key, value in best.params.items():
            print(f"  {key}: {value}")
        
        print(f"\n📈 性能指标:")
        print(f"  总收益率: {best.total_return:.2f}%")
        print(f"  夏普比率: {best.sharpe_ratio:.4f}")
        print(f"  最大回撤: {best.max_drawdown:.2f}%")
        print(f"  胜率: {best.win_rate:.2f}%")
        print(f"  交易次数: {best.total_trades}")
        print(f"  综合评分: {best.score:.4f}")
        
        if not args.no_update_config:
            print(f"\n✅ 配置文件已更新: {args.config}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 优化被用户中断")
    except Exception as e:
        print(f"\n❌ 优化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
