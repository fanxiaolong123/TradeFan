#!/usr/bin/env python3
"""
TradeFan 指标库测试脚本
=====================

测试indicators_lib中所有指标函数的基本功能。
使用模拟的BTC价格数据进行测试。

Author: TradeFan Team
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings('ignore')  # 忽略警告信息

try:
    from indicators_lib import trend, momentum, volatility, volume, risk, composite
    from indicators_lib import INDICATOR_MAP, list_indicators
    print("✅ 成功导入indicators_lib模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


def generate_btc_test_data(days: int = 100) -> pd.DataFrame:
    """生成BTC测试数据"""
    print(f"📊 生成{days}天的BTC测试数据...")
    
    # 时间序列
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 模拟BTC价格走势
    np.random.seed(42)
    initial_price = 45000
    
    # 生成价格序列 (包含趋势和随机波动)
    trend_component = np.linspace(0, 0.2, days)  # 20%的上升趋势
    noise = np.random.normal(0, 0.02, days)     # 2%的日波动
    seasonal = 0.05 * np.sin(2 * np.pi * np.arange(days) / 30)  # 月度季节性
    
    returns = trend_component / days + noise + seasonal / days
    
    # 计算价格
    prices = [initial_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # 生成OHLCV数据
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        # 模拟日内波动
        daily_range = close * 0.03  # 3%的日内波动
        high = close + np.random.uniform(0, daily_range)
        low = close - np.random.uniform(0, daily_range)
        open_price = prices[i-1] if i > 0 else close
        
        # 确保OHLC逻辑正确
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = np.random.randint(20000, 100000)  # 随机成交量
        
        data.append({
            'date': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    
    print(f"✅ 生成完成 - 价格范围: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
    return df


def test_trend_indicators(data: pd.DataFrame) -> dict:
    """测试趋势指标"""
    print("\n📈 测试趋势指标...")
    results = {}
    
    try:
        # 基础移动平均
        results['sma_20'] = trend.sma(data['close'], 20)
        results['ema_20'] = trend.ema(data['close'], 20)
        results['dema_20'] = trend.dema(data['close'], 20)
        results['tema_20'] = trend.tema(data['close'], 20)
        results['wma_20'] = trend.wma(data['close'], 20)
        results['hma_20'] = trend.hma(data['close'], 20)
        
        # VWAP
        results['vwap'] = trend.vwap(data['high'], data['low'], data['close'], data['volume'])
        
        # MACD
        macd_line, signal_line, histogram = trend.macd(data['close'])
        results['macd_line'] = macd_line
        results['macd_signal'] = signal_line
        results['macd_histogram'] = histogram
        
        # PPO
        ppo_line, ppo_signal, ppo_hist = trend.ppo(data['close'])
        results['ppo_line'] = ppo_line
        
        # ADX
        adx_val, plus_di, minus_di = trend.adx(data['high'], data['low'], data['close'])
        results['adx'] = adx_val
        results['plus_di'] = plus_di
        results['minus_di'] = minus_di
        
        # Parabolic SAR
        results['sar'] = trend.parabolic_sar(data['high'], data['low'])
        
        # TRIX
        results['trix'] = trend.trix(data['close'])
        
        # Aroon
        aroon_up, aroon_down = trend.aroon(data['high'], data['low'])
        results['aroon_up'] = aroon_up
        results['aroon_down'] = aroon_down
        
        print("✅ 趋势指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
    except Exception as e:
        print(f"❌ 趋势指标测试失败: {e}")
    
    return results


def test_momentum_indicators(data: pd.DataFrame) -> dict:
    """测试动量指标"""
    print("\n⚡ 测试动量指标...")
    results = {}
    
    try:
        # RSI
        results['rsi'] = momentum.rsi(data['close'])
        results['stoch_rsi_k'], results['stoch_rsi_d'] = momentum.stoch_rsi(data['close'])
        
        # CCI
        results['cci'] = momentum.cci(data['high'], data['low'], data['close'])
        
        # ROC
        results['roc'] = momentum.roc(data['close'])
        
        # Momentum
        results['momentum'] = momentum.momentum(data['close'])
        
        # Stochastic
        results['stoch_k'], results['stoch_d'] = momentum.stochastic_kd(
            data['high'], data['low'], data['close']
        )
        
        # Williams %R
        results['williams_r'] = momentum.williams_r(data['high'], data['low'], data['close'])
        
        # Ultimate Oscillator
        results['uo'] = momentum.ultimate_oscillator(data['high'], data['low'], data['close'])
        
        # Awesome Oscillator
        results['ao'] = momentum.awesome_oscillator(data['high'], data['low'])
        
        # MFI
        results['mfi'] = momentum.mfi(data['high'], data['low'], data['close'], data['volume'])
        
        # TSI
        results['tsi'] = momentum.tsi(data['close'])
        
        # DPO
        results['dpo'] = momentum.dpo(data['close'])
        
        # KAMA
        results['kama'] = momentum.kama(data['close'])
        
        print("✅ 动量指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
    except Exception as e:
        print(f"❌ 动量指标测试失败: {e}")
    
    return results


def test_volatility_indicators(data: pd.DataFrame) -> dict:
    """测试波动率指标"""
    print("\n📊 测试波动率指标...")
    results = {}
    
    try:
        # ATR
        results['atr'] = volatility.atr(data['high'], data['low'], data['close'])
        results['natr'] = volatility.natr(data['high'], data['low'], data['close'])
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = volatility.bollinger_bands(data['close'])
        results['bb_upper'] = bb_upper
        results['bb_middle'] = bb_middle
        results['bb_lower'] = bb_lower
        
        # Donchian Channel
        dc_upper, dc_lower = volatility.donchian_channel(data['high'], data['low'])
        results['dc_upper'] = dc_upper
        results['dc_lower'] = dc_lower
        
        # Keltner Channel
        kc_upper, kc_middle, kc_lower = volatility.keltner_channel(
            data['high'], data['low'], data['close']
        )
        results['kc_upper'] = kc_upper
        results['kc_middle'] = kc_middle
        results['kc_lower'] = kc_lower
        
        # Volatility
        results['volatility'] = volatility.volatility(data['close'])
        results['std_dev'] = volatility.std_dev(data['close'])
        
        # Ulcer Index
        results['ulcer_index'] = volatility.ulcer_index(data['close'])
        
        # Mass Index
        results['mass_index'] = volatility.mass_index(data['high'], data['low'])
        
        # Chaikin Volatility
        results['chaikin_vol'] = volatility.chaikin_volatility(data['high'], data['low'])
        
        # Bollinger Bands Width & %B
        results['bb_width'] = volatility.bollinger_bands_width(data['close'])
        results['bb_percent_b'] = volatility.bollinger_bands_percent_b(data['close'])
        
        print("✅ 波动率指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
    except Exception as e:
        print(f"❌ 波动率指标测试失败: {e}")
    
    return results


def test_volume_indicators(data: pd.DataFrame) -> dict:
    """测试成交量指标"""
    print("\n📊 测试成交量指标...")
    results = {}
    
    try:
        # OBV
        results['obv'] = volume.obv(data['close'], data['volume'])
        
        # Volume SMA
        results['volume_sma'] = volume.volume_sma(data['volume'])
        
        # Chaikin Money Flow
        results['cmf'] = volume.chaikin_money_flow(
            data['high'], data['low'], data['close'], data['volume']
        )
        
        # A/D Line
        results['ad_line'] = volume.accumulation_distribution(
            data['high'], data['low'], data['close'], data['volume']
        )
        
        # Volume ROC
        results['volume_roc'] = volume.volume_rate_of_change(data['volume'])
        
        # Ease of Movement
        results['eom'] = volume.ease_of_movement(data['high'], data['low'], data['volume'])
        
        # Volume Oscillator
        results['volume_osc'] = volume.volume_oscillator(data['volume'])
        
        # PVT
        results['pvt'] = volume.price_volume_trend(data['close'], data['volume'])
        
        # NVI/PVI
        results['nvi'] = volume.negative_volume_index(data['close'], data['volume'])
        results['pvi'] = volume.positive_volume_index(data['close'], data['volume'])
        
        # VWMA
        results['vwma'] = volume.volume_weighted_moving_average(data['close'], data['volume'])
        
        # Klinger Oscillator
        klinger_osc, klinger_signal = volume.klinger_oscillator(
            data['high'], data['low'], data['close'], data['volume']
        )
        results['klinger_osc'] = klinger_osc
        results['klinger_signal'] = klinger_signal
        
        # Force Index
        results['force_index'] = volume.force_index(data['close'], data['volume'])
        
        print("✅ 成交量指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
    except Exception as e:
        print(f"❌ 成交量指标测试失败: {e}")
    
    return results


def test_risk_indicators(data: pd.DataFrame) -> dict:
    """测试风险指标"""
    print("\n🛡️ 测试风险指标...")
    results = {}
    
    try:
        # 计算收益率
        returns = data['close'].pct_change().dropna()
        
        # 假设市场收益率 (简化处理)
        market_returns = returns * 0.8 + np.random.normal(0, 0.01, len(returns))
        market_returns.index = returns.index
        
        # 净值序列
        net_value = (1 + returns).cumprod()
        
        # 测试各种风险指标
        results['sharpe_ratio'] = risk.sharpe_ratio(returns)
        results['sortino_ratio'] = risk.sortino_ratio(returns)
        results['max_drawdown'] = risk.max_drawdown(net_value)
        results['calmar_ratio'] = risk.calmar_ratio(returns)
        results['var_95'] = risk.var(returns, 0.05)
        results['cvar_95'] = risk.cvar(returns, 0.05)
        results['beta'] = risk.beta(returns, market_returns)
        results['alpha'] = risk.alpha(returns, market_returns)
        results['information_ratio'] = risk.information_ratio(returns, market_returns)
        results['tracking_error'] = risk.tracking_error(returns, market_returns)
        results['omega_ratio'] = risk.omega_ratio(returns)
        results['pain_index'] = risk.pain_index(net_value)
        results['ulcer_index'] = risk.ulcer_index(net_value)
        results['downside_risk'] = risk.downside_risk(returns)
        
        print("✅ 风险指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
        # 打印一些关键指标
        print(f"   夏普比率: {results['sharpe_ratio']:.3f}")
        print(f"   最大回撤: {results['max_drawdown']:.2%}")
        print(f"   贝塔系数: {results['beta']:.3f}")
        
    except Exception as e:
        print(f"❌ 风险指标测试失败: {e}")
    
    return results


def test_composite_indicators(data: pd.DataFrame, other_results: dict) -> dict:
    """测试组合指标"""
    print("\n🔧 测试组合指标...")
    results = {}
    
    try:
        # 趋势强度指标 (需要MACD和ADX)
        if 'macd_histogram' in other_results and 'adx' in other_results:
            results['trend_strength'] = composite.trend_strength_indicator(
                other_results['macd_histogram'], other_results['adx']
            )
        
        # 波动率突破
        if 'bb_upper' in other_results and 'bb_lower' in other_results:
            results['volatility_breakout'] = composite.volatility_breakout(
                data['close'], other_results['bb_upper'], other_results['bb_lower'], data['volume']
            )
        
        # 支撑阻力
        support, resistance = composite.support_resistance(
            data['high'], data['low'], data['close']
        )
        results['support'] = support
        results['resistance'] = resistance
        
        # 一目均衡表
        ichimoku = composite.ichimoku_cloud(data['high'], data['low'], data['close'])
        results.update(ichimoku)
        
        # 枢轴点
        pivots = composite.pivot_points(data['high'], data['low'], data['close'])
        results.update(pivots)
        
        # 动量背离 (使用RSI)
        if 'rsi' in other_results:
            results['momentum_divergence'] = composite.momentum_divergence(
                data['close'], other_results['rsi']
            )
        
        # 多时间框架信号
        results['multi_timeframe'] = composite.multi_timeframe_signal(data['close'])
        
        # 市场状态检测
        results['market_regime'] = composite.market_regime_detection(
            data['close'], data['volume']
        )
        
        # 斐波那契回撤
        fib_levels = composite.fibonacci_retracement(data['high'], data['low'])
        results.update(fib_levels)
        
        # 量价分析
        vpa = composite.volume_price_analysis(data['close'], data['volume'])
        results.update(vpa)
        
        # 综合动量评分
        results['composite_momentum'] = composite.composite_momentum_score(
            data['close'], data['high'], data['low'], data['volume']
        )
        
        print("✅ 组合指标测试完成")
        print(f"   计算了{len(results)}个指标")
        
    except Exception as e:
        print(f"❌ 组合指标测试失败: {e}")
    
    return results


def test_indicator_map():
    """测试指标映射功能"""
    print("\n🗺️ 测试指标映射功能...")
    
    try:
        # 测试列出所有指标
        all_indicators = list_indicators()
        print(f"✅ 总共可用指标: {len(all_indicators)}个")
        
        # 按类别列出
        for category in ['trend', 'momentum', 'volatility', 'volume', 'risk', 'composite']:
            indicators = list_indicators(category)
            print(f"   {category}: {len(indicators)}个指标")
        
        # 测试动态获取指标函数
        from indicators_lib import get_indicator
        ema_func = get_indicator('ema')
        print(f"✅ 动态获取EMA函数: {ema_func}")
        
        print("✅ 指标映射功能测试完成")
        
    except Exception as e:
        print(f"❌ 指标映射功能测试失败: {e}")


def main():
    """主测试函数"""
    print("🚀 TradeFan 指标库全面测试")
    print("=" * 50)
    
    # 生成测试数据
    btc_data = generate_btc_test_data(100)
    
    # 测试各类指标
    all_results = {}
    
    # 趋势指标
    trend_results = test_trend_indicators(btc_data)
    all_results.update(trend_results)
    
    # 动量指标
    momentum_results = test_momentum_indicators(btc_data)
    all_results.update(momentum_results)
    
    # 波动率指标
    volatility_results = test_volatility_indicators(btc_data)
    all_results.update(volatility_results)
    
    # 成交量指标
    volume_results = test_volume_indicators(btc_data)
    all_results.update(volume_results)
    
    # 风险指标
    risk_results = test_risk_indicators(btc_data)
    all_results.update(risk_results)
    
    # 组合指标
    composite_results = test_composite_indicators(btc_data, all_results)
    all_results.update(composite_results)
    
    # 测试指标映射
    test_indicator_map()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print(f"✅ 成功计算了 {len(all_results)} 个指标值")
    print(f"📈 测试数据: {len(btc_data)} 天BTC价格数据")
    print(f"💰 价格范围: ${btc_data['close'].min():.0f} - ${btc_data['close'].max():.0f}")
    
    # 检查结果有效性
    valid_results = 0
    for name, result in all_results.items():
        if isinstance(result, (pd.Series, float, int)) and not pd.isna(result).all():
            valid_results += 1
    
    print(f"✅ 有效结果: {valid_results}/{len(all_results)} ({valid_results/len(all_results)*100:.1f}%)")
    
    if valid_results / len(all_results) > 0.8:
        print("🎉 测试通过！指标库运行正常。")
    else:
        print("⚠️ 部分指标可能存在问题，请检查具体实现。")
    
    return all_results


if __name__ == "__main__":
    try:
        results = main()
        print("\n🎯 可以开始使用indicators_lib进行策略开发了！")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc() 