#!/bin/bash
# TradeFan 生产环境设置脚本
# 安全设置API密钥环境变量

echo "🔐 TradeFan 生产环境API密钥设置"
echo "=================================================="

# 检查是否已设置环境变量
if [[ -n "$BINANCE_API_KEY" && -n "$BINANCE_API_SECRET" ]]; then
    echo "✅ 检测到已设置的环境变量"
    echo "🔑 API Key: ${BINANCE_API_KEY:0:8}...${BINANCE_API_KEY: -8}"
    echo "🔐 API Secret: ${BINANCE_API_SECRET:0:8}...${BINANCE_API_SECRET: -8}"
    
    read -p "🤔 是否重新设置? (y/N): " reset_env
    if [[ "$reset_env" != "y" && "$reset_env" != "Y" ]]; then
        echo "✅ 使用现有环境变量"
        exit 0
    fi
fi

echo ""
echo "⚠️  重要安全提醒:"
echo "1. 请确保您的API密钥权限设置正确"
echo "2. 建议启用IP白名单限制"
echo "3. 定期更换API密钥"
echo "4. 不要在公共场所输入密钥"
echo ""

# 安全输入API密钥
echo "📝 请输入您的Binance API凭证:"
read -p "🔑 API Key: " api_key
read -s -p "🔐 API Secret: " api_secret
echo ""

# 验证输入
if [[ -z "$api_key" || -z "$api_secret" ]]; then
    echo "❌ API密钥不能为空"
    exit 1
fi

if [[ ${#api_key} -lt 32 || ${#api_secret} -lt 32 ]]; then
    echo "❌ API密钥长度不正确"
    exit 1
fi

# 设置环境变量
export BINANCE_API_KEY="$api_key"
export BINANCE_API_SECRET="$api_secret"

# 保存到当前会话
echo "export BINANCE_API_KEY=\"$api_key\"" > .env_production
echo "export BINANCE_API_SECRET=\"$api_secret\"" >> .env_production

echo "✅ 环境变量设置完成"
echo "🔑 API Key: ${api_key:0:8}...${api_key: -8}"
echo "🔐 API Secret: ${api_secret:0:8}...${api_secret: -8}"

echo ""
echo "💡 使用方法:"
echo "1. 当前会话已设置环境变量"
echo "2. 新会话请运行: source .env_production"
echo "3. 或者运行: source setup_production_env.sh"

echo ""
echo "🚀 现在可以启动生产交易:"
echo "python3 start_production_trading.py"
