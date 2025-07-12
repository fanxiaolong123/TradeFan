#!/usr/bin/env python3
"""
TradeFan 部署前检查脚本
验证系统配置、API连接、策略参数等

运行方式:
python3 scripts/pre_deployment_check.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.config_manager import get_config_manager
from modules.binance_connector import BinanceConnector
from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy


class PreDeploymentChecker:
    """部署前检查器"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.config_manager = get_config_manager()
        self.check_results = {}
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def run_all_checks(self) -> bool:
        """运行所有检查"""
        print("🔍 TradeFan 部署前系统检查")
        print("=" * 50)
        
        checks = [
            ("系统环境检查", self._check_system_environment),
            ("配置文件检查", self._check_configuration),
            ("API连接检查", self._check_api_connection),
            ("策略验证检查", self._check_strategies),
            ("依赖包检查", self._check_dependencies),
            ("资金安全检查", self._check_capital_safety),
            ("风险参数检查", self._check_risk_parameters),
            ("交易对检查", self._check_trading_pairs)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                result = await check_func()
                self.check_results[check_name] = result
                
                if result['passed']:
                    print(f"   ✅ {check_name}通过")
                    if result.get('details'):
                        for detail in result['details']:
                            print(f"      • {detail}")
                else:
                    print(f"   ❌ {check_name}失败")
                    all_passed = False
                    if result.get('errors'):
                        for error in result['errors']:
                            print(f"      ❌ {error}")
                    if result.get('warnings'):
                        for warning in result['warnings']:
                            print(f"      ⚠️ {warning}")
                            
            except Exception as e:
                print(f"   ❌ {check_name}检查出错: {e}")
                self.check_results[check_name] = {
                    'passed': False,
                    'errors': [str(e)]
                }
                all_passed = False
        
        # 生成检查报告
        await self._generate_report()
        
        return all_passed
    
    async def _check_system_environment(self) -> dict:
        """检查系统环境"""
        result = {'passed': True, 'details': [], 'warnings': []}
        
        try:
            # 检查Python版本
            python_version = sys.version_info
            if python_version >= (3, 9):
                result['details'].append(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro} ✓")
            else:
                result['passed'] = False
                result['errors'] = [f"Python版本过低: {python_version.major}.{python_version.minor}, 需要3.9+"]
            
            # 检查必要目录
            required_dirs = ['logs', 'data', 'results', 'config']
            for dir_name in required_dirs:
                if os.path.exists(dir_name):
                    result['details'].append(f"目录 {dir_name} 存在 ✓")
                else:
                    os.makedirs(dir_name, exist_ok=True)
                    result['details'].append(f"创建目录 {dir_name} ✓")
            
            # 检查磁盘空间
            import shutil
            disk_usage = shutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            if free_gb > 1:
                result['details'].append(f"可用磁盘空间: {free_gb:.1f}GB ✓")
            else:
                result['warnings'].append(f"磁盘空间不足: {free_gb:.1f}GB")
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"系统环境检查失败: {e}"]
        
        return result
    
    async def _check_configuration(self) -> dict:
        """检查配置文件"""
        result = {'passed': True, 'details': [], 'errors': []}
        
        try:
            # 加载生产配置
            config = self.config_manager.load_config("production")
            
            # 检查关键配置项
            if config.trading.initial_capital > 0:
                result['details'].append(f"初始资金: ${config.trading.initial_capital} ✓")
            else:
                result['errors'].append("初始资金配置错误")
                result['passed'] = False
            
            if config.trading.max_risk_per_trade <= 0.05:
                result['details'].append(f"单笔风险: {config.trading.max_risk_per_trade:.1%} ✓")
            else:
                result['errors'].append("单笔风险过高")
                result['passed'] = False
            
            # 检查交易所配置
            if config.exchanges and len(config.exchanges) > 0:
                exchange = config.exchanges[0]
                result['details'].append(f"交易所: {exchange.name} ✓")
                result['details'].append(f"测试网模式: {exchange.sandbox} ✓")
                
                if exchange.api_key:
                    result['details'].append("API Key已配置 ✓")
                else:
                    result['errors'].append("API Key未配置")
                    result['passed'] = False
            else:
                result['errors'].append("交易所配置缺失")
                result['passed'] = False
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"配置检查失败: {e}"]
        
        return result
    
    async def _check_api_connection(self) -> dict:
        """检查API连接"""
        result = {'passed': True, 'details': [], 'errors': []}
        
        try:
            config = self.config_manager.load_config("production")
            exchange = config.exchanges[0]
            
            # 获取API密钥
            api_secret = os.getenv('BINANCE_API_SECRET')
            if not api_secret:
                result['errors'].append("BINANCE_API_SECRET环境变量未设置")
                result['passed'] = False
                return result
            
            # 测试API连接
            async with BinanceConnector(
                exchange.api_key, 
                api_secret, 
                testnet=True  # 强制使用测试网
            ) as connector:
                # 连接测试
                connectivity = await connector.test_connectivity()
                if connectivity:
                    result['details'].append("API连接测试通过 ✓")
                else:
                    result['errors'].append("API连接测试失败")
                    result['passed'] = False
                    return result
                
                # 获取账户信息
                account_info = await connector.get_account_info()
                if account_info:
                    result['details'].append("账户信息获取成功 ✓")
                    
                    # 检查余额
                    balances = await connector.get_balance()
                    usdt_balance = balances.get('USDT', {}).get('free', 0)
                    result['details'].append(f"USDT余额: {usdt_balance} ✓")
                    
                    if usdt_balance < 100:  # 测试网至少需要100 USDT
                        result['errors'].append("测试网USDT余额不足，请先获取测试币")
                        result['passed'] = False
                
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"API连接检查失败: {e}"]
        
        return result
    
    async def _check_strategies(self) -> dict:
        """检查策略"""
        result = {'passed': True, 'details': [], 'errors': []}
        
        try:
            # 测试短线策略
            scalping_config = {
                'ema_fast': 8, 'ema_medium': 21, 'ema_slow': 55,
                'rsi_period': 14, 'signal_threshold': 0.6
            }
            
            scalping_strategy = ScalpingStrategy(scalping_config)
            result['details'].append("短线策略初始化成功 ✓")
            
            # 测试趋势策略
            trend_config = {
                'ema_fast': 8, 'ema_medium': 21, 'ema_slow': 55,
                'adx_threshold': 25, 'trend_strength_threshold': 0.6
            }
            
            trend_strategy = TrendFollowingStrategy(trend_config)
            result['details'].append("趋势跟踪策略初始化成功 ✓")
            
            # 测试策略信息
            scalping_info = scalping_strategy.get_strategy_info()
            trend_info = trend_strategy.get_strategy_info()
            
            result['details'].append(f"短线策略类型: {scalping_info.get('type', 'Unknown')} ✓")
            result['details'].append(f"趋势策略类型: {trend_info.get('type', 'Unknown')} ✓")
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"策略检查失败: {e}"]
        
        return result
    
    async def _check_dependencies(self) -> dict:
        """检查依赖包"""
        result = {'passed': True, 'details': [], 'warnings': []}
        
        required_packages = [
            'pandas', 'numpy', 'aiohttp', 'pyyaml'
        ]
        
        optional_packages = [
            'ta-lib', 'scikit-learn', 'matplotlib'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                result['details'].append(f"必需包 {package} 已安装 ✓")
            except ImportError:
                result['passed'] = False
                result['errors'] = result.get('errors', [])
                result['errors'].append(f"缺少必需包: {package}")
        
        for package in optional_packages:
            try:
                __import__(package)
                result['details'].append(f"可选包 {package} 已安装 ✓")
            except ImportError:
                result['warnings'].append(f"可选包 {package} 未安装")
        
        return result
    
    async def _check_capital_safety(self) -> dict:
        """检查资金安全"""
        result = {'passed': True, 'details': [], 'warnings': []}
        
        try:
            config = self.config_manager.load_config("production")
            
            # 检查初始资金
            initial_capital = config.trading.initial_capital
            if initial_capital <= 1000:
                result['details'].append(f"初始资金适中: ${initial_capital} ✓")
            else:
                result['warnings'].append(f"初始资金较大: ${initial_capital}，建议先小额测试")
            
            # 检查风险参数
            max_risk = config.trading.max_risk_per_trade
            if max_risk <= 0.02:
                result['details'].append(f"单笔风险合理: {max_risk:.1%} ✓")
            else:
                result['warnings'].append(f"单笔风险较高: {max_risk:.1%}")
            
            # 检查止损设置
            stop_loss = config.trading.stop_loss
            if 0.01 <= stop_loss <= 0.05:
                result['details'].append(f"止损设置合理: {stop_loss:.1%} ✓")
            else:
                result['warnings'].append(f"止损设置需要关注: {stop_loss:.1%}")
            
            # 检查测试网设置
            exchange = config.exchanges[0]
            if exchange.sandbox:
                result['details'].append("使用测试网，资金安全 ✓")
            else:
                result['warnings'].append("使用实盘模式，请确认资金安全")
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"资金安全检查失败: {e}"]
        
        return result
    
    async def _check_risk_parameters(self) -> dict:
        """检查风险参数"""
        result = {'passed': True, 'details': [], 'warnings': []}
        
        try:
            config = self.config_manager.load_config("production")
            
            # 风险参数检查
            risk_checks = [
                ("最大回撤", config.trading.max_drawdown, 0.05, 0.20),
                ("日最大损失", config.trading.max_daily_loss, 0.02, 0.10),
                ("单笔风险", config.trading.max_risk_per_trade, 0.005, 0.03),
                ("止损比例", config.trading.stop_loss, 0.01, 0.05)
            ]
            
            for name, value, min_safe, max_safe in risk_checks:
                if min_safe <= value <= max_safe:
                    result['details'].append(f"{name}: {value:.1%} (安全范围) ✓")
                elif value < min_safe:
                    result['warnings'].append(f"{name}过于保守: {value:.1%}")
                else:
                    result['warnings'].append(f"{name}风险较高: {value:.1%}")
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"风险参数检查失败: {e}"]
        
        return result
    
    async def _check_trading_pairs(self) -> dict:
        """检查交易对"""
        result = {'passed': True, 'details': [], 'warnings': []}
        
        try:
            config = self.config_manager.load_config("production")
            exchange = config.exchanges[0]
            
            # 检查交易对配置
            symbols = [s.symbol for s in exchange.symbols if s.enabled]
            result['details'].append(f"启用的交易对数量: {len(symbols)} ✓")
            
            for symbol_config in exchange.symbols:
                if symbol_config.enabled:
                    symbol = symbol_config.symbol
                    capital = symbol_config.capital
                    strategy = symbol_config.strategy
                    
                    result['details'].append(f"{symbol}: ${capital:.2f} ({strategy}) ✓")
                    
                    if capital < 50:
                        result['warnings'].append(f"{symbol}资金较少: ${capital:.2f}")
            
            # 检查总资金分配
            total_allocated = sum(s.capital for s in exchange.symbols if s.enabled)
            if abs(total_allocated - config.trading.initial_capital) < 1:
                result['details'].append(f"资金分配合理: ${total_allocated:.2f} ✓")
            else:
                result['warnings'].append(f"资金分配不匹配: 总计${total_allocated:.2f}, 配置${config.trading.initial_capital}")
            
        except Exception as e:
            result['passed'] = False
            result['errors'] = [f"交易对检查失败: {e}"]
        
        return result
    
    async def _generate_report(self):
        """生成检查报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': all(r.get('passed', False) for r in self.check_results.values()),
                'checks': self.check_results
            }
            
            # 保存报告
            os.makedirs('reports', exist_ok=True)
            report_file = f"reports/pre_deployment_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\n📄 详细检查报告已保存: {report_file}")
            
        except Exception as e:
            print(f"⚠️ 报告生成失败: {e}")


async def main():
    """主函数"""
    checker = PreDeploymentChecker()
    
    try:
        success = await checker.run_all_checks()
        
        print("\n" + "=" * 50)
        if success:
            print("✅ 所有检查通过！系统已准备好部署")
            print("\n🚀 下一步操作:")
            print("   1. 设置 BINANCE_API_SECRET 环境变量")
            print("   2. 运行回测: python3 run_comprehensive_backtest.py")
            print("   3. 启动测试交易: python3 start_production_trading.py --mode live --test-mode")
            print("   4. 监控系统状态")
        else:
            print("❌ 部分检查未通过，请修复问题后重新检查")
            print("\n🔧 修复建议:")
            print("   1. 检查错误信息并逐一修复")
            print("   2. 安装缺失的依赖包")
            print("   3. 配置正确的API密钥")
            print("   4. 调整风险参数")
        
        return success
        
    except Exception as e:
        print(f"❌ 检查过程出错: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 检查被用户中断")
        sys.exit(1)
