# 自动交易系统

一个结构清晰、可扩展的Python自动交易系统，支持多币种趋势策略，具备完整的风险控制和回测功能。

## 🚀 主要特性

- **模块化架构**: 清晰的模块分离，易于维护和扩展
- **多币种支持**: 支持BTC、ETH、BNB、SOL等主流币种
- **趋势策略**: 内置趋势跟踪策略，结合移动平均线、ADX、唐奇安通道
- **风险控制**: 完善的仓位管理、止损止盈、最大回撤控制
- **回测系统**: 支持历史数据回测，输出详细的性能分析
- **实时监控**: 账户状态、持仓盈亏、风险指标实时监控
- **日志系统**: 完整的交易日志记录和事件追踪

## 📁 项目结构

```
trading_system/
├── config/                 # 配置文件
│   └── config.yaml        # 主配置文件
├── modules/               # 核心模块
│   ├── data_module.py     # 数据获取模块
│   ├── strategy_module.py # 策略模块
│   ├── risk_control_module.py # 风险控制模块
│   ├── execution_module.py # 执行模块
│   ├── backtest_module.py # 回测模块
│   ├── monitor_module.py  # 监控模块
│   ├── log_module.py      # 日志模块
│   └── utils.py          # 工具类
├── examples/              # 示例代码
├── logs/                  # 日志文件
├── data/                  # 数据缓存
├── results/               # 回测结果
├── main.py               # 主程序
├── requirements.txt      # 依赖包
└── README.md            # 说明文档
```

## 🛠️ 安装配置

### 1. 环境要求

- Python 3.10+
- TA-Lib 技术分析库

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository_url>
cd trading_system

# 安装Python依赖
pip install -r requirements.txt

# 安装TA-Lib (macOS)
brew install ta-lib

# 安装TA-Lib (Ubuntu)
sudo apt-get install libta-lib-dev

# 安装TA-Lib (Windows)
# 下载对应版本的whl文件安装
```

### 3. 配置设置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件，添加API密钥
vim .env
```

在 `.env` 文件中设置：
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET=your_secret_here
```

### 4. 配置参数

编辑 `config/config.yaml` 文件，调整交易参数：

```yaml
# 交易币种配置
symbols:
  - symbol: "BTC/USDT"
    enabled: true
    strategy_params:
      fast_ma: 20
      slow_ma: 50
      adx_period: 14

# 风险控制配置
risk_control:
  max_position_size: 0.1    # 单币种最大仓位10%
  stop_loss: 0.02          # 2%止损
  take_profit: 0.04        # 4%止盈
  initial_capital: 10000   # 初始资金
```

## 🎯 使用方法

### 回测模式

```bash
# 使用默认配置运行回测
python main.py --mode backtest

# 指定币种和策略
python main.py --mode backtest --symbols BTC/USDT ETH/USDT --strategy TrendFollowing

# 使用自定义配置文件
python main.py --mode backtest --config my_config.yaml
```

### 实盘交易模式

```bash
# 运行实盘交易（谨慎使用）
python main.py --mode live
```

### 运行示例

```bash
# 运行回测示例
python examples/run_backtest.py
```

## 📊 策略说明

### 趋势跟踪策略 (TrendFollowing)

结合多个技术指标的综合趋势策略：

- **移动平均线**: 快线(20)和慢线(50)判断趋势方向
- **ADX指标**: 衡量趋势强度，过滤弱势行情
- **唐奇安通道**: 突破信号确认
- **RSI过滤**: 避免超买超卖区域入场

**买入条件**:
- 快线上穿慢线
- ADX > 25 (趋势强度足够)
- +DI > -DI (多头趋势)
- 价格突破唐奇安通道上轨
- RSI < 70 (非超买)

**卖出条件**:
- 快线下穿慢线
- ADX > 25
- +DI < -DI (空头趋势)
- 价格跌破唐奇安通道下轨
- RSI > 30 (非超卖)

## 🛡️ 风险控制

### 仓位管理
- 单币种最大仓位限制
- 总仓位限制
- 动态仓位调整

### 止损止盈
- 固定比例止损
- 固定比例止盈
- 实时监控触发

### 回撤控制
- 最大回撤限制
- 动态风险调整
- 紧急停止机制

## 📈 回测结果

系统会自动生成以下回测报告：

- **权益曲线图**: 资金变化趋势
- **回撤曲线图**: 风险控制效果
- **交易记录**: 详细的买卖记录
- **性能指标**: 收益率、夏普比率、最大回撤等

### 主要指标说明

- **总收益率**: 整个回测期间的总收益
- **年化收益率**: 按年计算的收益率
- **夏普比率**: 风险调整后收益指标
- **最大回撤**: 最大亏损幅度
- **胜率**: 盈利交易占比
- **盈亏比**: 平均盈利/平均亏损

## 🔧 扩展开发

### 添加新策略

1. 在 `strategy_module.py` 中继承 `BaseStrategy` 类
2. 实现 `generate_signals()` 和 `calculate_indicators()` 方法
3. 在 `StrategyManager` 中注册新策略

```python
class MyStrategy(BaseStrategy):
    def generate_signals(self, data):
        # 实现信号生成逻辑
        pass
    
    def calculate_indicators(self, data):
        # 实现指标计算逻辑
        pass
```

### 添加新指标

使用TA-Lib库添加技术指标：

```python
import talib

# 在策略中计算新指标
rsi = talib.RSI(data['close'].values, timeperiod=14)
macd, signal, hist = talib.MACD(data['close'].values)
```

### 自定义风控规则

在 `RiskControlModule` 中添加新的风控逻辑：

```python
def custom_risk_check(self, symbol, amount, price):
    # 实现自定义风控逻辑
    return True, "通过检查", amount
```

## 📝 日志系统

系统提供完整的日志记录：

- **交易日志**: 所有买卖操作记录
- **策略日志**: 信号生成和指标计算
- **风控日志**: 风险控制事件
- **系统日志**: 运行状态和错误信息

日志文件保存在 `logs/` 目录下，支持按大小自动轮转。

## ⚠️ 风险提示

1. **本系统仅供学习和研究使用**
2. **实盘交易存在资金损失风险**
3. **请在充分测试后谨慎使用实盘模式**
4. **建议先使用小额资金测试**
5. **市场有风险，投资需谨慎**

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至: [your-email@example.com]

---

**免责声明**: 本软件仅用于教育和研究目的。使用本软件进行实际交易的任何损失，开发者不承担责任。请在充分了解风险的情况下使用。
