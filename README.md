# TradeFan - 专业量化交易系统

高性能加密货币量化交易平台，支持多策略、多时间框架的自动化交易。

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置API
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的交易所API密钥
```

### 运行回测
```bash
# 专业回测演示
python3 demos/quick_professional_experience.py

# 短线交易回测
python3 demos/scalping_demo.py
```

### 启动实盘交易
```bash
# 模拟交易 (推荐)
python3 start_live_trading.py --paper

# 实盘交易 (谨慎使用)
python3 start_live_trading.py
```

## 📊 优化成果

基于历史回测数据的策略优化结果：

### PEPE/USDT 策略
- **4小时策略**: 32.15% 收益率 (优化前: 7.23%)
- **日线策略**: 24.88% 收益率 (优化前: 4.19%)
- **胜率**: 43.7% - 50.8%

### DOGE/USDT 多时间框架策略
- **最佳配置**: 4h-1h-30m 组合
- **收益率**: 6.89%
- **胜率**: 63.33%
- **最大回撤**: 0.89%

### BTC 专业策略
- **总收益**: 75.75% (vs BTC 42.08%)
- **年化收益**: 118.31%
- **夏普比率**: 2.59
- **最大回撤**: 13.05%

## ⚠️ 风险提示

- 量化交易存在风险，请谨慎投资
- 建议先使用模拟交易测试策略
- 不要投入超过承受能力的资金
- 定期监控和调整策略参数

## 📁 项目结构

```
TradeFan/
├── config/          # 配置文件
├── strategies/      # 交易策略
├── modules/         # 核心模块
├── demos/          # 演示程序
├── results/        # 回测结果
├── logs/           # 日志文件
└── data/           # 数据文件
```

## 🛠️ 主要功能

- ✅ 多交易所支持 (Binance, OKX等)
- ✅ 多策略框架 (短线、趋势、套利)
- ✅ 多时间框架分析 (5m-1d)
- ✅ 专业风险控制
- ✅ 实时监控和报警
- ✅ 机构级回测分析

---

**版本**: v2.0.0  
**作者**: TradeFan Team  
**许可**: MIT License
