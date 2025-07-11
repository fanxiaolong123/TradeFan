# 📊 TradeFan 策略工程工具包 - indicators_lib

一个全面的技术分析指标库，专为TradeFan量化交易系统设计。提供**70+**专业技术指标，不依赖TA-Lib，纯Python实现，便于维护和扩展。

## 🚀 特性亮点

- **🎯 全面覆盖**: 趋势、动量、波动性、成交量、风险、组合指标6大类别
- **⚡ 高性能**: 纯pandas/numpy实现，计算速度快
- **🔧 易用性**: 统一的API设计，支持动态调用
- **📊 专业级**: 包含夏普比率、最大回撤等专业风险指标
- **🛠️ 可扩展**: 模块化设计，易于添加新指标

## 📦 安装说明

indicators_lib是TradeFan项目的一部分，无需额外安装。确保已安装项目依赖：

```bash
pip install pandas numpy
```

## 🎯 快速开始

### 基础使用

```python
import pandas as pd
from indicators_lib import trend, momentum, volatility

# 假设你有OHLCV数据
df = pd.read_csv('btc_data.csv')

# 计算技术指标
df['ema_20'] = trend.ema(df['close'], 20)
df['rsi_14'] = momentum.rsi(df['close'], 14)

# 布林带
upper, middle, lower = volatility.bollinger_bands(df['close'], 20)
df['bb_upper'] = upper
df['bb_middle'] = middle  
df['bb_lower'] = lower
```

### 动态调用

```python
from indicators_lib import get_indicator, list_indicators

# 查看所有可用指标
all_indicators = list_indicators()
print(f"总共{len(all_indicators)}个指标")

# 按类别查看
trend_indicators = list_indicators('trend')
print(f"趋势指标: {trend_indicators}")

# 动态获取指标函数
ema_func = get_indicator('ema')
result = ema_func(df['close'], 20)
```

## 📚 指标分类详解

### 📈 趋势指标 (trend.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| 简单移动平均 | `sma(series, window)` | 经典趋势指标 |
| 指数移动平均 | `ema(series, window)` | 对近期价格权重更高 |
| MACD | `macd(series, fast, slow, signal)` | 返回MACD线、信号线、直方图 |
| ADX | `adx(high, low, close, window)` | 趋势强度指标 |
| 抛物转向 | `parabolic_sar(high, low, af, max_af)` | 止损和反转信号 |
| 船体移动平均 | `hma(series, window)` | 减少滞后的移动平均 |
| VWAP | `vwap(high, low, close, volume)` | 成交量加权平均价格 |

```python
# 使用示例
from indicators_lib import trend

# MACD指标
macd_line, signal_line, histogram = trend.macd(df['close'], 12, 26, 9)

# ADX趋势强度
adx_value, plus_di, minus_di = trend.adx(df['high'], df['low'], df['close'], 14)
```

### ⚡ 动量指标 (momentum.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| RSI | `rsi(series, window)` | 相对强弱指数 |
| 随机指标 | `stochastic_kd(high, low, close, k_window, d_window)` | 返回%K和%D |
| CCI | `cci(high, low, close, window)` | 商品通道指数 |
| 威廉指标 | `williams_r(high, low, close, window)` | Williams %R |
| 资金流量指数 | `mfi(high, low, close, volume, window)` | 结合成交量的RSI |
| 变化率 | `roc(series, window)` | 价格变化率 |

```python
# 使用示例
from indicators_lib import momentum

# RSI指标
rsi = momentum.rsi(df['close'], 14)

# 随机指标
k_percent, d_percent = momentum.stochastic_kd(df['high'], df['low'], df['close'])
```

### 📊 波动性指标 (volatility.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| ATR | `atr(high, low, close, window)` | 平均真实区间 |
| 布林带 | `bollinger_bands(series, window, std)` | 返回上轨、中轨、下轨 |
| 唐奇安通道 | `donchian_channel(high, low, window)` | 突破交易经典指标 |
| 肯特纳通道 | `keltner_channel(high, low, close, window, multiplier)` | 基于ATR的通道 |
| 历史波动率 | `volatility(series, window)` | 年化波动率 |
| 溃疡指数 | `ulcer_index(close, window)` | 衡量回撤深度 |

```python
# 使用示例
from indicators_lib import volatility

# 布林带
upper, middle, lower = volatility.bollinger_bands(df['close'], 20, 2.0)

# ATR
atr_value = volatility.atr(df['high'], df['low'], df['close'], 14)
```

### 📊 成交量指标 (volume.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| OBV | `obv(close, volume)` | 能量潮指标 |
| 蔡金资金流量 | `chaikin_money_flow(high, low, close, volume, window)` | CMF指标 |
| 累积分布线 | `accumulation_distribution(high, low, close, volume)` | A/D Line |
| 成交量震荡器 | `volume_oscillator(volume, short_window, long_window)` | 成交量动量 |
| 强力指数 | `force_index(close, volume, window)` | 价格与成交量结合 |

```python
# 使用示例  
from indicators_lib import volume

# OBV指标
obv_value = volume.obv(df['close'], df['volume'])

# 蔡金资金流量
cmf = volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume'])
```

### 🛡️ 风险指标 (risk.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| 夏普比率 | `sharpe_ratio(returns, risk_free_rate, periods)` | 风险调整收益 |
| 最大回撤 | `max_drawdown(net_value_series)` | 最大回撤比例 |
| 索提诺比率 | `sortino_ratio(returns, target_return, periods)` | 下行风险调整收益 |
| VaR | `var(returns, confidence_level)` | 风险价值 |
| CVaR | `cvar(returns, confidence_level)` | 条件风险价值 |
| 贝塔系数 | `beta(returns, market_returns)` | 系统性风险 |

```python
# 使用示例
from indicators_lib import risk

# 计算收益率
returns = df['close'].pct_change().dropna()
net_value = (1 + returns).cumprod()

# 风险指标
sharpe = risk.sharpe_ratio(returns)
max_dd = risk.max_drawdown(net_value)
var_95 = risk.var(returns, 0.05)
```

### 🔧 组合指标 (composite.py)

| 指标 | 函数 | 说明 |
|------|------|------|
| 趋势强度 | `trend_strength_indicator(macd_histogram, adx, threshold)` | 综合趋势评分 |
| 波动率突破 | `volatility_breakout(close, upper_band, lower_band, volume)` | 突破信号 |
| 支撑阻力 | `support_resistance(high, low, close, window, strength)` | 关键价位识别 |
| 一目均衡表 | `ichimoku_cloud(high, low, close, tenkan_period, kijun_period, senkou_period)` | 日式技术分析 |
| 综合动量评分 | `composite_momentum_score(close, high, low, volume)` | 多指标动量综合 |

```python
# 使用示例
from indicators_lib import composite

# 趋势强度指标
_, _, macd_hist = trend.macd(df['close'])
adx_val, _, _ = trend.adx(df['high'], df['low'], df['close'])
trend_strength = composite.trend_strength_indicator(macd_hist, adx_val)

# 一目均衡表
ichimoku = composite.ichimoku_cloud(df['high'], df['low'], df['close'])
```

## 🧪 测试运行

运行完整的测试套件来验证所有指标：

```bash
cd indicators_lib
python test_indicators.py
```

测试脚本会：
- 生成100天的模拟BTC数据
- 测试所有70+指标的计算
- 验证结果的有效性
- 展示性能统计

## 💡 实战案例

### 案例1: 布林带突破策略

```python
from indicators_lib import volatility, composite

# 计算布林带
upper, middle, lower = volatility.bollinger_bands(df['close'], 20, 2.0)

# 突破信号
breakout_signals = composite.volatility_breakout(
    df['close'], upper, lower, df['volume']
)

# 策略信号
df['signal'] = 0
df.loc[breakout_signals == 1, 'signal'] = 1   # 买入
df.loc[breakout_signals == -1, 'signal'] = -1 # 卖出
```

### 案例2: 多指标过滤系统

```python
from indicators_lib import trend, momentum, volatility

# 趋势过滤
df['ema_fast'] = trend.ema(df['close'], 12)
df['ema_slow'] = trend.ema(df['close'], 26)
trend_up = df['ema_fast'] > df['ema_slow']

# 动量确认
df['rsi'] = momentum.rsi(df['close'], 14)
momentum_ok = (df['rsi'] > 30) & (df['rsi'] < 70)

# 波动率控制
df['atr'] = volatility.atr(df['high'], df['low'], df['close'], 14)
volatility_normal = df['atr'] < df['atr'].rolling(50).quantile(0.8)

# 综合信号
df['final_signal'] = trend_up & momentum_ok & volatility_normal
```

### 案例3: 风险监控系统

```python
from indicators_lib import risk

# 滚动风险计算
window = 30
returns = df['close'].pct_change()

risk_metrics = []
for i in range(window, len(returns)):
    period_returns = returns.iloc[i-window:i]
    period_value = (1 + period_returns).cumprod()
    
    metrics = {
        'date': df.index[i],
        'sharpe': risk.sharpe_ratio(period_returns),
        'max_dd': risk.max_drawdown(period_value),
        'var_95': risk.var(period_returns, 0.05)
    }
    risk_metrics.append(metrics)

risk_df = pd.DataFrame(risk_metrics)
```

## 🔧 高级功能

### 自定义指标组合

```python
from indicators_lib import get_indicator

def custom_signal(df, fast=12, slow=26, rsi_period=14):
    """自定义交易信号"""
    
    # 动态获取指标函数
    ema_func = get_indicator('ema')
    rsi_func = get_indicator('rsi')
    
    # 计算指标
    ema_fast = ema_func(df['close'], fast)
    ema_slow = ema_func(df['close'], slow)
    rsi = rsi_func(df['close'], rsi_period)
    
    # 生成信号
    signal = pd.Series(0, index=df.index)
    signal[(ema_fast > ema_slow) & (rsi < 70)] = 1
    signal[(ema_fast < ema_slow) & (rsi > 30)] = -1
    
    return signal
```

### 批量指标计算

```python
from indicators_lib import INDICATOR_MAP, list_indicators

def calculate_all_indicators(df):
    """批量计算所有适用的指标"""
    results = {}
    
    # 趋势指标
    for indicator_name in list_indicators('trend'):
        try:
            func = INDICATOR_MAP[indicator_name]
            if indicator_name in ['sma', 'ema', 'dema', 'tema']:
                results[indicator_name] = func(df['close'], 20)
            elif indicator_name == 'macd':
                macd, signal, hist = func(df['close'])
                results['macd'] = macd
                results['macd_signal'] = signal
                results['macd_histogram'] = hist
            # ... 其他指标
        except Exception as e:
            print(f"计算{indicator_name}时出错: {e}")
    
    return results
```

## 📊 性能优化建议

1. **批量计算**: 一次性计算多个指标比逐个计算更高效
2. **缓存结果**: 对于相同参数的指标，缓存计算结果
3. **数据预处理**: 确保输入数据格式正确，避免重复转换
4. **内存管理**: 对于大数据集，考虑分批处理

## 🤝 扩展开发

### 添加新指标

```python
# 在对应模块中添加新函数
def my_custom_indicator(series: pd.Series, window: int = 14) -> pd.Series:
    """
    自定义指标
    
    Args:
        series: 价格序列
        window: 计算窗口期
        
    Returns:
        指标值序列
    """
    # 你的计算逻辑
    result = series.rolling(window).apply(lambda x: your_calculation(x))
    return result

# 添加到__all__列表
__all__.append('my_custom_indicator')
```

### 更新指标映射

```python
# 在__init__.py中添加到INDICATOR_MAP
INDICATOR_MAP['my_custom_indicator'] = module.my_custom_indicator
```

## 📝 注意事项

1. **数据格式**: 所有函数接受pandas.Series输入
2. **缺失值**: 指标计算会产生NaN值，属正常现象
3. **参数调整**: 默认参数适用于日线数据，其他周期需调整
4. **性能考虑**: 复杂指标计算可能较慢，建议缓存结果

## 🔗 相关链接

- [TradeFan主项目](../README.md)
- [策略开发指南](../docs/user-guides/quick-start.md)
- [API文档](../docs/api/)

## 📄 许可证

本项目采用MIT许可证，详见项目根目录LICENSE文件。

---

**🎯 让TradeFan成为行业顶尖的策略交易机器人！**

*indicators_lib - 为专业量化交易而生的技术指标武器库* 