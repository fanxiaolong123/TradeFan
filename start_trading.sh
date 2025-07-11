#!/bin/bash

# 自动交易系统启动脚本

echo "🚀 自动交易系统启动脚本"
echo "=========================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 ./install.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置
if [ ! -f ".env" ]; then
    echo "❌ .env 文件不存在，请先配置API密钥"
    echo "💡 参考 TESTNET_SETUP.md 进行配置"
    exit 1
fi

# 显示菜单
echo ""
echo "请选择启动模式："
echo ""
echo "📊 基础功能:"
echo "1) 🧪 系统测试 (test_system.py)"
echo "2) 📈 演示回测 (simple_demo.py)"
echo "3) 📊 监控仪表板 (dashboard.py)"
echo ""
echo "🔄 实时交易:"
echo "4) 🔄 模拟交易系统 (live_trading.py)"
echo "5) 🏭 生产环境交易 (production_trading.py) ⚠️"
echo ""
echo "🔧 参数优化:"
echo "6) 🎯 参数优化 - 网格搜索"
echo "7) 🎯 参数优化 - 贝叶斯优化"
echo "8) 🎯 参数优化 - 随机搜索"
echo ""
echo "🤖 AI功能:"
echo "9) 🤖 AI策略生成器"
echo "10) 🤖 AI策略循环优化"
echo ""
echo "📋 其他:"
echo "11) 📄 查看系统状态"
echo "12) 📊 生成优化报告"
echo "13) ❌ 退出"
echo ""

read -p "请输入选择 (1-13): " choice

case $choice in
    1)
        echo "🧪 运行系统测试..."
        python test_system.py
        ;;
    2)
        echo "📈 运行演示回测..."
        python simple_demo.py
        ;;
    3)
        echo "📊 启动监控仪表板..."
        echo "🌐 访问地址: http://localhost:5000"
        echo "💡 按 Ctrl+C 停止服务"
        echo ""
        python dashboard.py
        ;;
    4)
        echo "🔄 启动模拟交易系统..."
        echo "💡 按 Ctrl+C 停止系统"
        echo "📊 系统状态将每5分钟输出一次"
        echo ""
        python live_trading.py
        ;;
    5)
        echo "⚠️  启动生产环境交易系统"
        echo "⚠️  这将使用真实资金进行交易！"
        echo ""
        read -p "确认启动生产环境? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            python production_trading.py
        else
            echo "取消启动"
        fi
        ;;
    6)
        echo "🎯 运行参数优化 - 网格搜索..."
        python optimize_params.py --method grid_search
        ;;
    7)
        echo "🎯 运行参数优化 - 贝叶斯优化..."
        python optimize_params.py --method bayesian --iterations 30
        ;;
    8)
        echo "🎯 运行参数优化 - 随机搜索..."
        python optimize_params.py --method random_search --iterations 50
        ;;
    9)
        echo "🤖 启动AI策略生成器..."
        echo "请选择市场条件:"
        echo "1) trending (趋势市场)"
        echo "2) sideways (震荡市场)" 
        echo "3) volatile (高波动市场)"
        read -p "选择 (1-3): " market_choice
        
        case $market_choice in
            1) market="trending" ;;
            2) market="sideways" ;;
            3) market="volatile" ;;
            *) market="trending" ;;
        esac
        
        python ai_strategy_manager.py --mode generate --market $market
        ;;
    10)
        echo "🤖 运行AI策略循环优化..."
        read -p "输入迭代次数 (默认5): " iterations
        iterations=${iterations:-5}
        python ai_strategy_manager.py --mode loop --iterations $iterations
        ;;
    11)
        echo "📄 查看系统状态..."
        echo ""
        echo "📊 系统信息:"
        echo "  Python版本: $(python --version)"
        echo "  虚拟环境: $(which python)"
        echo "  当前目录: $(pwd)"
        echo ""
        echo "📁 文件状态:"
        echo "  配置文件: $([ -f config/config.yaml ] && echo '✅ 存在' || echo '❌ 不存在')"
        echo "  环境变量: $([ -f .env ] && echo '✅ 存在' || echo '❌ 不存在')"
        echo "  日志目录: $([ -d logs ] && echo '✅ 存在' || echo '❌ 不存在')"
        echo "  结果目录: $([ -d results ] && echo '✅ 存在' || echo '❌ 不存在')"
        echo ""
        echo "📦 已安装包:"
        pip list | grep -E "(pandas|numpy|matplotlib|ccxt|scikit-learn|flask|websockets)"
        ;;
    12)
        echo "📊 生成优化报告..."
        if [ -d "results/optimization" ]; then
            echo "📁 优化结果文件:"
            ls -la results/optimization/ | tail -10
        else
            echo "❌ 暂无优化结果"
        fi
        
        if [ -d "strategies/ai_generated" ]; then
            echo ""
            echo "🤖 AI生成的策略:"
            ls -la strategies/ai_generated/ | tail -5
        else
            echo "❌ 暂无AI生成的策略"
        fi
        ;;
    13)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
