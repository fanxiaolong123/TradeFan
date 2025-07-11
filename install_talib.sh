#!/bin/bash

echo "🔧 TradeFan TA-Lib 安装脚本"
echo "================================"

# 检测操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "检测到 macOS 系统"
    
    # 检查是否安装了 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "❌ 未检测到 Homebrew，正在安装..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "✅ Homebrew 已安装"
    fi
    
    # 安装 ta-lib 系统依赖
    echo "📦 安装 TA-Lib 系统依赖..."
    brew install ta-lib
    
    # 安装 Python 包
    echo "🐍 安装 Python TA-Lib 包..."
    pip3 install TA-Lib
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "检测到 Linux 系统"
    
    # Ubuntu/Debian
    if command -v apt-get &> /dev/null; then
        echo "📦 安装 TA-Lib 系统依赖 (Ubuntu/Debian)..."
        sudo apt-get update
        sudo apt-get install -y build-essential wget
        
        # 下载并编译 TA-Lib
        cd /tmp
        wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib/
        ./configure --prefix=/usr
        make
        sudo make install
        
        # 安装 Python 包
        pip3 install TA-Lib
        
    # CentOS/RHEL
    elif command -v yum &> /dev/null; then
        echo "📦 安装 TA-Lib 系统依赖 (CentOS/RHEL)..."
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y wget
        
        # 下载并编译 TA-Lib
        cd /tmp
        wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
        tar -xzf ta-lib-0.4.0-src.tar.gz
        cd ta-lib/
        ./configure --prefix=/usr
        make
        sudo make install
        
        # 安装 Python 包
        pip3 install TA-Lib
    fi
    
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    echo "请手动安装 TA-Lib"
    exit 1
fi

# 验证安装
echo "🧪 验证 TA-Lib 安装..."
python3 -c "import talib; print('✅ TA-Lib 安装成功！版本:', talib.__version__)" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "🎉 TA-Lib 安装完成！"
else
    echo "❌ TA-Lib 安装失败，请检查错误信息"
    echo ""
    echo "🔧 手动安装方法："
    echo "1. macOS: brew install ta-lib && pip3 install TA-Lib"
    echo "2. Ubuntu: sudo apt-get install libta-lib-dev && pip3 install TA-Lib"
    echo "3. 或使用 conda: conda install -c conda-forge ta-lib"
fi
