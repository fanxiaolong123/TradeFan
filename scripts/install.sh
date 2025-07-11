#!/bin/bash

# 自动交易系统安装脚本

echo "=========================================="
echo "自动交易系统安装脚本"
echo "=========================================="

# 检查Python版本
echo "检查Python版本..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✓ Python版本符合要求: $python_version"
else
    echo "✗ Python版本过低，需要3.10+，当前版本: $python_version"
    exit 1
fi

# 创建虚拟环境
echo "创建Python虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
else
    echo "✓ 虚拟环境已存在"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装Python依赖包..."
pip install -r requirements.txt

# 检查TA-Lib
echo "检查TA-Lib安装..."
if python3 -c "import talib" 2>/dev/null; then
    echo "✓ TA-Lib已安装"
else
    echo "⚠️  TA-Lib未安装，尝试安装..."
    
    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "使用Homebrew安装TA-Lib..."
            brew install ta-lib
            pip install TA-Lib
        else
            echo "请先安装Homebrew，然后运行: brew install ta-lib"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "Linux系统，请手动安装TA-Lib:"
        echo "sudo apt-get install libta-lib-dev"
        echo "pip install TA-Lib"
    else
        echo "请根据您的操作系统手动安装TA-Lib"
    fi
fi

# 创建必要目录
echo "创建必要目录..."
mkdir -p logs data results

# 复制配置文件
echo "设置配置文件..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ 已创建.env文件，请编辑添加API密钥"
else
    echo "✓ .env文件已存在"
fi

# 运行测试
echo "运行系统测试..."
python3 test_system.py

echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 编辑 .env 文件，添加您的API密钥"
echo "2. 编辑 config/config.yaml 调整交易参数"
echo "3. 运行测试: python test_system.py"
echo "4. 运行回测: python main.py --mode backtest"
echo "5. 查看示例: python examples/run_backtest.py"
echo ""
echo "注意事项："
echo "- 请先在测试环境中验证系统"
echo "- 实盘交易前请充分测试"
echo "- 投资有风险，请谨慎操作"
echo ""
