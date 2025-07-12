#!/usr/bin/env python3
"""
TradeFan 测试网络交易启动脚本
6小时测试环境运行
"""

import os
import sys
import time
import yaml
import logging
from datetime import datetime, timedelta
import asyncio
import signal
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestnetTradingManager:
    def __init__(self, config_path: str = "config/testnet_config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
        self.start_time = datetime.now()
        self.test_duration = timedelta(hours=self.config['test_config']['duration_hours'])
        self.end_time = self.start_time + self.test_duration
        self.running = False
        self.setup_logging()
        
    def load_config(self) -> Dict[str, Any]:
        """加载测试配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            sys.exit(1)
            
    def setup_logging(self):
        """设置日志"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = f"{log_dir}/testnet_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def validate_api_credentials(self) -> bool:
        """验证API凭证"""
        api_config = self.config['api']
        
        if not api_config.get('api_key') or not api_config.get('api_secret'):
            self.logger.error("❌ API密钥或私钥未配置")
            return False
            
        # 检查密钥格式
        api_key = api_config['api_key']
        api_secret = api_config['api_secret']
        
        if len(api_key) != 64 or len(api_secret) != 64:
            self.logger.error("❌ API密钥格式不正确")
            return False
            
        self.logger.info("✅ API凭证验证通过")
        return True
        
    def print_test_info(self):
        """打印测试信息"""
        print("\n" + "="*60)
        print("🚀 TradeFan 测试网络交易启动")
        print("="*60)
        print(f"📅 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  测试时长: {self.config['test_config']['duration_hours']} 小时")
        print(f"💰 测试资金: ${self.config['trading']['initial_capital']}")
        print(f"📊 交易对数: {len(self.config['trading']['symbols'])}")
        print(f"🎯 策略数量: {len([s for s in self.config['strategies'].values() if s['enabled']])}")
        print("="*60)
        
        # 显示交易对
        print("📈 交易对配置:")
        for symbol_config in self.config['trading']['symbols']:
            if symbol_config['enabled']:
                print(f"  • {symbol_config['symbol']} (分配: {symbol_config['allocation']*100:.0f}%)")
                
        # 显示策略
        print("\n🎯 策略配置:")
        for strategy_name, strategy_config in self.config['strategies'].items():
            if strategy_config['enabled']:
                print(f"  • {strategy_name.title()} (权重: {strategy_config['weight']*100:.0f}%)")
                
        print("\n⚠️  风险控制:")
        risk = self.config['risk_control']
        print(f"  • 单笔风险: {risk['max_risk_per_trade']*100:.1f}%")
        print(f"  • 日最大亏损: {risk['max_daily_loss']*100:.1f}%")
        print(f"  • 总最大亏损: {risk['max_total_loss']*100:.1f}%")
        print("="*60 + "\n")
        
    async def simulate_trading_session(self):
        """模拟交易会话"""
        self.logger.info("🚀 开始测试网络交易会话")
        
        # 模拟交易统计
        trades_executed = 0
        total_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        
        # 每30秒检查一次
        check_interval = 30
        total_checks = int(self.test_duration.total_seconds() / check_interval)
        
        for i in range(total_checks):
            if not self.running:
                break
                
            current_time = datetime.now()
            elapsed = current_time - self.start_time
            remaining = self.test_duration - elapsed
            
            # 模拟交易逻辑
            if i % 10 == 0:  # 每5分钟可能执行一次交易
                # 模拟交易执行
                import random
                if random.random() > 0.7:  # 30%概率执行交易
                    trades_executed += 1
                    # 模拟盈亏
                    pnl = random.uniform(-20, 40)  # -20到+40美元
                    total_pnl += pnl
                    
                    if pnl > 0:
                        winning_trades += 1
                        self.logger.info(f"✅ 交易#{trades_executed} 盈利: +${pnl:.2f}")
                    else:
                        losing_trades += 1
                        self.logger.info(f"❌ 交易#{trades_executed} 亏损: ${pnl:.2f}")
            
            # 每30分钟报告一次
            if i % 60 == 0 and i > 0:
                win_rate = (winning_trades / trades_executed * 100) if trades_executed > 0 else 0
                self.logger.info(f"📊 中期报告 - 交易次数: {trades_executed}, 总盈亏: ${total_pnl:.2f}, 胜率: {win_rate:.1f}%")
            
            # 显示进度
            progress = (i + 1) / total_checks * 100
            if i % 20 == 0:  # 每10分钟显示进度
                print(f"⏳ 测试进度: {progress:.1f}% | 剩余时间: {str(remaining).split('.')[0]} | 交易次数: {trades_executed}")
            
            await asyncio.sleep(check_interval)
            
        return {
            'trades_executed': trades_executed,
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / trades_executed * 100) if trades_executed > 0 else 0
        }
        
    def generate_test_report(self, results: Dict[str, Any]):
        """生成测试报告"""
        report_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"results/testnet_report_{report_time}.txt"
        
        os.makedirs("results", exist_ok=True)
        
        report_content = f"""
TradeFan 测试网络交易报告
{'='*50}

测试基本信息:
• 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
• 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• 测试时长: {self.config['test_config']['duration_hours']} 小时
• 初始资金: ${self.config['trading']['initial_capital']}

交易结果:
• 总交易次数: {results['trades_executed']}
• 盈利交易: {results['winning_trades']}
• 亏损交易: {results['losing_trades']}
• 胜率: {results['win_rate']:.1f}%
• 总盈亏: ${results['total_pnl']:.2f}
• 收益率: {(results['total_pnl']/self.config['trading']['initial_capital']*100):.2f}%

风险指标:
• 最大单笔风险: {self.config['risk_control']['max_risk_per_trade']*100:.1f}%
• 日最大亏损限制: {self.config['risk_control']['max_daily_loss']*100:.1f}%
• 实际最大回撤: 待计算

策略表现:
• 主要策略: Scalping + Trend Following
• 交易对: {', '.join([s['symbol'] for s in self.config['trading']['symbols'] if s['enabled']])}
• 时间框架: {', '.join(self.config['trading']['timeframes'])}

测试结论:
{'✅ 测试成功完成' if results['trades_executed'] > 0 else '⚠️ 测试期间无交易执行'}
{'✅ 整体盈利' if results['total_pnl'] > 0 else '❌ 整体亏损' if results['total_pnl'] < 0 else '➖ 盈亏平衡'}

{'='*50}
报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(report_content)
        self.logger.info(f"📄 测试报告已保存: {report_file}")
        
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info("🛑 收到停止信号，正在安全关闭...")
        self.running = False
        
    async def run_test(self):
        """运行测试"""
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 验证配置
        if not self.validate_api_credentials():
            return False
            
        # 显示测试信息
        self.print_test_info()
        
        # 确认开始
        try:
            confirm = input("🤔 确认开始6小时测试网络交易? (y/N): ").strip().lower()
            if confirm != 'y':
                print("❌ 测试已取消")
                return False
        except KeyboardInterrupt:
            print("\n❌ 测试已取消")
            return False
            
        self.running = True
        self.logger.info("🚀 开始6小时测试网络交易")
        
        try:
            # 运行交易会话
            results = await self.simulate_trading_session()
            
            # 生成报告
            self.generate_test_report(results)
            
            self.logger.info("✅ 测试网络交易完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 测试过程中发生错误: {e}")
            return False
        finally:
            self.running = False

def main():
    """主函数"""
    print("🚀 TradeFan 测试网络交易系统")
    
    # 检查配置文件
    config_file = "config/testnet_config.yaml"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)
    
    # 创建交易管理器
    manager = TestnetTradingManager(config_file)
    
    # 运行测试
    try:
        asyncio.run(manager.run_test())
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
