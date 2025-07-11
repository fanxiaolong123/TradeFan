#!/usr/bin/env python3
"""
项目状态检查和下一步指导脚本
自动检测当前项目状态，并给出具体的下一步行动建议
"""

import sys
import os
import subprocess
from pathlib import Path

def check_python_packages():
    """检查Python包安装状态"""
    packages = {
        'ccxt': 'CCXT交易所连接库',
        'pandas': 'Pandas数据处理库', 
        'numpy': 'NumPy数值计算库',
        'matplotlib': 'Matplotlib绘图库',
        'yaml': 'PyYAML配置文件库',
        'dotenv': 'Python-dotenv环境变量库',
        'loguru': 'Loguru日志库'
    }
    
    results = {}
    for package, description in packages.items():
        try:
            if package == 'yaml':
                import yaml
            elif package == 'dotenv':
                import dotenv
            else:
                __import__(package)
            results[package] = True
        except ImportError:
            results[package] = False
    
    return results

def check_talib():
    """检查TA-Lib安装状态"""
    try:
        import talib
        return True, talib.__version__
    except ImportError:
        return False, None

def check_api_config():
    """检查API配置状态"""
    env_file = Path('.env')
    if not env_file.exists():
        return False, "环境变量文件不存在"
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    if 'your_api_key_here' in content or 'your_secret_here' in content:
        return False, "API密钥未配置"
    
    if 'BINANCE_API_KEY=' in content and 'BINANCE_SECRET=' in content:
        return True, "API密钥已配置"
    
    return False, "API密钥配置不完整"

def check_system_tests():
    """检查系统测试状态"""
    try:
        result = subprocess.run([sys.executable, 'test_basic_system.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, "基础系统测试通过"
        else:
            return False, f"基础系统测试失败: {result.stderr}"
    except Exception as e:
        return False, f"无法运行系统测试: {e}"

def check_data_connection():
    """检查数据连接状态"""
    try:
        import ccxt
        exchange = ccxt.binance({'sandbox': True, 'enableRateLimit': True})
        markets = exchange.load_markets()
        return True, f"数据连接正常，找到{len(markets)}个交易对"
    except Exception as e:
        return False, f"数据连接失败: {e}"

def generate_next_steps(checks):
    """根据检查结果生成下一步建议"""
    steps = []
    priority = 1
    
    # 检查基础依赖
    if not all(checks['packages'].values()):
        missing = [pkg for pkg, status in checks['packages'].items() if not status]
        steps.append({
            'priority': priority,
            'title': '安装缺失的Python包',
            'command': f'pip3 install {" ".join(missing)}',
            'description': f'缺失包: {", ".join(missing)}'
        })
        priority += 1
    
    # 检查TA-Lib
    if not checks['talib'][0]:
        steps.append({
            'priority': priority,
            'title': '安装TA-Lib技术分析库',
            'command': './install_talib.sh',
            'description': 'TA-Lib是技术指标计算的核心依赖'
        })
        priority += 1
    
    # 检查API配置
    if not checks['api_config'][0]:
        steps.append({
            'priority': priority,
            'title': '配置API密钥',
            'command': 'vim .env',
            'description': checks['api_config'][1]
        })
        priority += 1
    
    # 检查系统测试
    if not checks['system_tests'][0]:
        steps.append({
            'priority': priority,
            'title': '运行系统测试',
            'command': 'python3 test_system.py',
            'description': checks['system_tests'][1]
        })
        priority += 1
    
    # 如果基础都OK，建议下一步
    if all([
        all(checks['packages'].values()),
        checks['talib'][0],
        checks['api_config'][0],
        checks['system_tests'][0]
    ]):
        steps.append({
            'priority': priority,
            'title': '运行真实数据回测',
            'command': 'python3 main.py --mode backtest --symbols BTC/USDT',
            'description': '系统基础功能正常，可以开始真实数据回测'
        })
        priority += 1
        
        steps.append({
            'priority': priority,
            'title': '策略参数优化',
            'command': 'python3 optimize_params.py',
            'description': '优化策略参数以提高收益率'
        })
        priority += 1
    
    return steps

def main():
    """主函数"""
    print("🔍 TradeFan 项目状态检查")
    print("=" * 50)
    
    # 执行各项检查
    checks = {
        'packages': check_python_packages(),
        'talib': check_talib(),
        'api_config': check_api_config(),
        'system_tests': check_system_tests(),
        'data_connection': check_data_connection()
    }
    
    # 显示检查结果
    print("📊 当前状态:")
    print("-" * 30)
    
    # Python包状态
    print("Python包:")
    for pkg, status in checks['packages'].items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {pkg}")
    
    # TA-Lib状态
    talib_status, talib_version = checks['talib']
    status_icon = "✅" if talib_status else "❌"
    version_info = f" (v{talib_version})" if talib_version else ""
    print(f"  {status_icon} TA-Lib{version_info}")
    
    # API配置状态
    api_status, api_msg = checks['api_config']
    status_icon = "✅" if api_status else "❌"
    print(f"  {status_icon} API配置: {api_msg}")
    
    # 系统测试状态
    test_status, test_msg = checks['system_tests']
    status_icon = "✅" if test_status else "❌"
    print(f"  {status_icon} 系统测试: {test_msg}")
    
    # 数据连接状态
    data_status, data_msg = checks['data_connection']
    status_icon = "✅" if data_status else "⚠️"
    print(f"  {status_icon} 数据连接: {data_msg}")
    
    print()
    
    # 生成下一步建议
    next_steps = generate_next_steps(checks)
    
    if not next_steps:
        print("🎉 恭喜！系统状态良好，可以开始高级功能开发")
        print()
        print("🚀 建议的下一步:")
        print("1. 策略优化和参数调优")
        print("2. 添加更多技术指标")
        print("3. 实现多策略组合")
        print("4. 开发Web监控界面")
        return
    
    print("🎯 下一步行动计划:")
    print("-" * 30)
    
    for step in next_steps:
        print(f"{step['priority']}. {step['title']}")
        print(f"   命令: {step['command']}")
        print(f"   说明: {step['description']}")
        print()
    
    # 给出立即执行的建议
    if next_steps:
        first_step = next_steps[0]
        print("💡 立即执行:")
        print(f"   {first_step['command']}")
        print()
    
    # 显示完整路线图
    print("📋 完整路线图请查看: PROJECT_ROADMAP.md")
    print("🔧 安装脚本请运行: ./install_talib.sh")
    print("📖 使用指南请查看: README.md")

if __name__ == "__main__":
    main()
