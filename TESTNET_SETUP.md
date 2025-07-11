# 🧪 Binance Testnet 配置指南

## 第1步：创建Binance Testnet账户

1. 访问 [Binance Testnet](https://testnet.binance.vision/)
2. 点击 "Login with GitHub" 使用GitHub账户登录
3. 登录后会自动创建测试账户

## 第2步：获取API密钥

1. 登录后点击右上角的用户头像
2. 选择 "API Management"
3. 点击 "Create API" 创建新的API密钥
4. 记录下 `API Key` 和 `Secret Key`

## 第3步：配置系统

### 更新 .env 文件

```bash
# 编辑 .env 文件
vim .env
```

添加你的Testnet API密钥：

```env
# Binance Testnet API 配置
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_SECRET=your_testnet_secret_here

# 其他配置
DEBUG=True
```

### 更新 config.yaml 文件

确保配置文件中启用了沙盒模式：

```yaml
exchange:
  name: "binance"
  sandbox: true  # 重要：使用测试网
  api_key: ""    # 从环境变量读取
  secret: ""     # 从环境变量读取
```

## 第4步：获取测试资金

1. 在Testnet页面点击 "Faucet"
2. 选择要获取的测试币种（BTC、ETH、BNB、USDT等）
3. 点击获取，测试资金会自动添加到账户

## 第5步：验证配置

运行测试脚本验证配置：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行系统测试
python test_system.py
```

## 第6步：启动实盘模拟交易

### 方式1：启动完整交易系统

```bash
# 启动实时交易系统
python live_trading.py
```

### 方式2：启动监控仪表板

```bash
# 启动Web监控面板
python dashboard.py
```

然后在浏览器中访问 http://localhost:5000

## 🔧 系统功能说明

### 实时交易系统 (live_trading.py)

- ✅ 实时WebSocket价格流
- ✅ 自动策略信号生成
- ✅ 风险控制检查
- ✅ 自动下单执行
- ✅ 止损止盈管理
- ✅ 实时状态监控

### 监控仪表板 (dashboard.py)

- 📊 账户余额监控
- 📋 持仓信息展示
- 📈 价格走势图表
- 🔄 交易记录查看
- 📊 交易统计分析

## ⚠️ 重要提醒

1. **这是测试环境**：所有交易都是模拟的，不涉及真实资金
2. **API限制**：Testnet有请求频率限制，避免过于频繁的请求
3. **数据延迟**：测试网数据可能有延迟，与实盘略有差异
4. **定期重置**：Testnet账户和数据会定期重置

## 🚀 下一步计划

完成Testnet测试后，可以考虑：

1. **参数优化**：调整策略参数，观察不同市场条件下的表现
2. **多策略测试**：添加更多交易策略进行对比
3. **风控优化**：完善风险控制机制
4. **监控增强**：添加更多监控指标和报警功能
5. **实盘准备**：在充分测试后考虑小额实盘交易

## 📞 问题排查

### 常见问题

**Q: API连接失败**
A: 检查API密钥是否正确，确保在.env文件中正确配置

**Q: WebSocket连接断开**
A: 网络问题导致，系统会自动重连

**Q: 无交易信号**
A: 检查策略参数，可能需要调整移动平均线周期

**Q: 余额不足**
A: 到Testnet Faucet获取更多测试资金

### 日志查看

```bash
# 查看交易日志
tail -f logs/trading.log

# 查看系统状态
python -c "from modules.monitor_module import MonitorModule; m = MonitorModule(); print(m.get_system_status())"
```

---

🎯 **目标**：通过1周的Testnet运行，验证系统稳定性和策略有效性，为后续实盘交易做好准备。
