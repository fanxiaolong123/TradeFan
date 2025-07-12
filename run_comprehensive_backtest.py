#!/usr/bin/env python3
"""
TradeFan 综合回测脚本
快速运行短线策略和趋势跟踪策略的完整回测

运行方式:
python3 run_comprehensive_backtest.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.multi_strategy_backtester import MultiStrategyBacktester


async def main():
    """主函数"""
    print("🚀 TradeFan 综合策略回测系统")
    print("=" * 60)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 创建回测器
        backtester = MultiStrategyBacktester({
            'initial_capital': 10000,
            'commission': 0.001,
            'slippage': 0.0005
        })
        
        print("📊 开始运行综合回测...")
        print("📅 回测期间: 2024-01-01 至 2024-06-30")
        print("💰 初始资金: $10,000")
        print("📈 交易对: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, PEPE/USDT, DOGE/USDT, WLD/USDT")
        print("⏰ 时间框架: 5m, 15m, 30m, 1h")
        print("🎯 策略: 短线策略 + 趋势跟踪策略")
        print()
        
        # 运行回测
        results = await backtester.run_comprehensive_backtest(
            start_date="2024-01-01",
            end_date="2024-06-30",
            timeframes=['5m', '15m', '30m', '1h']
        )
        
        # 显示结果
        print("\n" + "=" * 60)
        print("📊 回测结果汇总")
        print("=" * 60)
        
        report = results.get('report', {})
        summary = report.get('summary', {})
        
        if summary:
            print(f"📋 总回测次数: {summary.get('total_backtests', 0)}")
            print(f"📈 平均收益率: {summary.get('avg_return', 0):.2%}")
            print(f"📊 平均夏普比率: {summary.get('avg_sharpe', 0):.2f}")
            print(f"📉 平均最大回撤: {summary.get('avg_max_drawdown', 0):.2%}")
            print(f"🎯 平均胜率: {summary.get('avg_win_rate', 0):.2%}")
            print(f"🏆 最佳收益率: {summary.get('best_return', 0):.2%}")
            print(f"📉 最差收益率: {summary.get('worst_return', 0):.2%}")
        
        # 最佳表现者
        best_performer = report.get('best_performers', {}).get('overall_best', {})
        if best_performer:
            print(f"\n🏆 最佳表现组合:")
            print(f"   策略: {best_performer.get('strategy', 'N/A')}")
            print(f"   交易对: {best_performer.get('symbol', 'N/A')}")
            print(f"   时间框架: {best_performer.get('timeframe', 'N/A')}")
            print(f"   收益率: {best_performer.get('return', 0):.2%}")
            print(f"   夏普比率: {best_performer.get('sharpe', 0):.2f}")
        
        # 策略对比
        strategy_comparison = report.get('strategy_comparison', {})
        if strategy_comparison:
            print(f"\n📊 策略对比:")
            for strategy, metrics in strategy_comparison.items():
                if isinstance(metrics, dict) and 'total_return' in metrics:
                    mean_return = metrics['total_return'].get('mean', 0)
                    mean_sharpe = metrics.get('sharpe_ratio', {}).get('mean', 0)
                    print(f"   {strategy}:")
                    print(f"     平均收益率: {mean_return:.2%}")
                    print(f"     平均夏普比率: {mean_sharpe:.2f}")
        
        # 交易对分析
        symbol_analysis = report.get('symbol_analysis', {})
        if symbol_analysis:
            print(f"\n💰 交易对表现:")
            for symbol, metrics in symbol_analysis.items():
                if isinstance(metrics, dict) and 'total_return' in metrics:
                    mean_return = metrics['total_return'].get('mean', 0)
                    print(f"   {symbol}: {mean_return:.2%}")
        
        # 建议
        recommendations = report.get('recommendations', [])
        if recommendations:
            print(f"\n💡 交易建议:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"   {i}. {rec}")
        
        print(f"\n📁 详细结果已保存到: results/multi_strategy_backtest/")
        print(f"✅ 回测完成!")
        
        # 生成部署建议
        print(f"\n🚀 生产部署建议:")
        print(f"   基于回测结果，建议的生产配置:")
        
        if best_performer:
            best_strategy = best_performer.get('strategy')
            best_symbol = best_performer.get('symbol')
            best_timeframe = best_performer.get('timeframe')
            
            print(f"   1. 优先部署 {best_strategy} 策略")
            print(f"   2. 重点关注 {best_symbol} 交易对")
            print(f"   3. 使用 {best_timeframe} 时间框架")
        
        print(f"   4. 建议初始资金: 每个策略 $500 (总计 $1000)")
        print(f"   5. 建议先使用测试网验证")
        
        return True
        
    except Exception as e:
        print(f"❌ 回测过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if success:
            print(f"\n🎉 回测成功完成!")
            print(f"📋 下一步:")
            print(f"   1. 查看详细结果文件")
            print(f"   2. 根据建议调整参数")
            print(f"   3. 运行生产部署: python3 start_production_trading.py --mode live --test-mode")
        else:
            print(f"\n❌ 回测失败，请检查错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️ 回测被用户中断")
        sys.exit(0)
