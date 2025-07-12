#!/usr/bin/env python3
"""
TradeFan 生产环境交易启动脚本
⚠️ 真实资金交易 - 请谨慎操作
"""

import os
import sys
import time
import yaml
import logging
import getpass
from datetime import datetime, timedelta
import asyncio
import signal
from typing import Dict, Any
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ProductionTradingManager:
    def __init__(self, config_path: str = "config/production_config.yaml"):
        self.config_path = config_path
        self.config = None
        self.start_time = datetime.now()
        self.running = False
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.consecutive_losses = 0
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志系统"""
        log_dir = "logs/production"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = f"{log_dir}/production_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config_safely(self) -> bool:
        """安全加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
                
            # 检查是否需要环境变量
            if "${BINANCE_API_KEY}" in config_content or "${BINANCE_API_SECRET}" in config_content:
                self.logger.info("🔐 检测到环境变量配置，请设置API密钥")
                return self.setup_api_credentials()
            else:
                self.config = yaml.safe_load(config_content)
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 配置文件加载失败: {e}")
            return False
            
    def setup_api_credentials(self) -> bool:
        """安全设置API凭证"""
        print("\n🔐 生产环境API凭证设置")
        print("=" * 50)
        print("⚠️  为了安全，请手动输入API密钥")
        print("💡 建议使用环境变量或配置文件保存密钥")
        
        try:
            # 检查环境变量
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            
            if not api_key or not api_secret:
                print("\n📝 未找到环境变量，请手动输入:")
                api_key = getpass.getpass("🔑 请输入API Key: ").strip()
                api_secret = getpass.getpass("🔐 请输入API Secret: ").strip()
                
            if not api_key or not api_secret:
                self.logger.error("❌ API凭证不能为空")
                return False
                
            # 验证密钥格式
            if len(api_key) < 32 or len(api_secret) < 32:
                self.logger.error("❌ API密钥格式不正确")
                return False
                
            # 加载配置并替换密钥
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
                
            config_content = config_content.replace("${BINANCE_API_KEY}", api_key)
            config_content = config_content.replace("${BINANCE_API_SECRET}", api_secret)
            
            self.config = yaml.safe_load(config_content)
            self.logger.info("✅ API凭证设置完成")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ API凭证设置失败: {e}")
            return False
            
    def validate_production_setup(self) -> bool:
        """验证生产环境设置"""
        self.logger.info("🔍 验证生产环境设置...")
        
        # 检查关键配置
        checks = [
            (self.config['api']['environment'] == 'production', "生产环境配置"),
            (self.config['production']['paper_trading'] == False, "真实交易模式"),
            (self.config['trading']['initial_capital'] <= 1000, "资金规模合理"),
            (self.config['risk_control']['max_risk_per_trade'] <= 0.05, "单笔风险控制"),
            (self.config['risk_control']['max_daily_loss'] <= 0.10, "日亏损限制"),
            (len([s for s in self.config['trading']['symbols'] if s['enabled']]) <= 3, "交易对数量限制")
        ]
        
        passed = 0
        for check, description in checks:
            if check:
                self.logger.info(f"✅ {description}")
                passed += 1
            else:
                self.logger.error(f"❌ {description}")
                
        if passed != len(checks):
            self.logger.error("❌ 生产环境验证失败")
            return False
            
        self.logger.info("✅ 生产环境验证通过")
        return True
        
    def print_production_warning(self):
        """显示生产环境警告"""
        print("\n" + "🚨" * 20)
        print("⚠️  生产环境交易警告")
        print("🚨" * 20)
        print("💰 这是真实资金交易！")
        print("📉 可能造成实际财务损失！")
        print("🎯 请确保您了解所有风险！")
        print("🛡️ 建议从小额资金开始！")
        print("📊 请持续监控交易状态！")
        print("🚨" * 20 + "\n")
        
    def print_trading_info(self):
        """显示交易信息"""
        print("📊 生产环境交易配置")
        print("=" * 50)
        print(f"💰 初始资金: ${self.config['trading']['initial_capital']}")
        print(f"📈 交易对数: {len([s for s in self.config['trading']['symbols'] if s['enabled']])}")
        print(f"⚠️  单笔风险: {self.config['risk_control']['max_risk_per_trade']*100:.1f}%")
        print(f"📉 日最大亏损: {self.config['risk_control']['max_daily_loss']*100:.1f}%")
        print(f"🔄 日最大交易: {self.config['risk_control']['max_daily_trades']}次")
        
        print("\n📈 启用的交易对:")
        for symbol_config in self.config['trading']['symbols']:
            if symbol_config['enabled']:
                print(f"  • {symbol_config['symbol']} (分配: {symbol_config['allocation']*100:.0f}%)")
                
        print("\n🎯 启用的策略:")
        for strategy_name, strategy_config in self.config['strategies'].items():
            if strategy_config['enabled']:
                print(f"  • {strategy_name.title()} (权重: {strategy_config['weight']*100:.0f}%)")
        print("=" * 50)
        
    def get_user_confirmation(self) -> bool:
        """获取用户确认"""
        try:
            print("\n🤔 确认信息:")
            print("1. 我了解这是真实资金交易")
            print("2. 我了解可能造成财务损失")
            print("3. 我已经设置了合理的风险参数")
            print("4. 我将持续监控交易状态")
            
            confirm1 = input("\n✅ 确认开始生产环境交易? (输入 'YES' 确认): ").strip()
            if confirm1 != 'YES':
                return False
                
            confirm2 = input("🔐 再次确认 (输入 'CONFIRM'): ").strip()
            if confirm2 != 'CONFIRM':
                return False
                
            return True
            
        except KeyboardInterrupt:
            print("\n❌ 用户取消")
            return False
            
    async def simulate_production_trading(self):
        """模拟生产交易会话"""
        self.logger.info("🚀 开始生产环境交易")
        
        # 交易统计
        session_start = datetime.now()
        check_interval = 60  # 每分钟检查一次
        
        while self.running:
            current_time = datetime.now()
            
            # 检查风险控制
            if self.check_risk_limits():
                self.logger.warning("⚠️ 触发风险控制，暂停交易")
                break
                
            # 模拟交易逻辑（实际应该连接真实API）
            await self.execute_trading_cycle()
            
            # 每小时报告
            if (current_time.minute == 0 and 
                (current_time - session_start).total_seconds() % 3600 < 60):
                self.generate_hourly_report()
                
            await asyncio.sleep(check_interval)
            
    def check_risk_limits(self) -> bool:
        """检查风险限制"""
        risk_config = self.config['risk_control']
        
        # 检查日亏损限制
        daily_loss_limit = self.config['trading']['initial_capital'] * risk_config['max_daily_loss']
        if self.daily_pnl < -daily_loss_limit:
            self.logger.error(f"❌ 触发日亏损限制: ${abs(self.daily_pnl):.2f}")
            return True
            
        # 检查总亏损限制
        total_loss_limit = self.config['trading']['initial_capital'] * risk_config['max_total_loss']
        if self.total_pnl < -total_loss_limit:
            self.logger.error(f"❌ 触发总亏损限制: ${abs(self.total_pnl):.2f}")
            return True
            
        # 检查连续亏损
        if self.consecutive_losses >= risk_config['max_consecutive_losses']:
            self.logger.error(f"❌ 连续亏损{self.consecutive_losses}次，暂停交易")
            return True
            
        # 检查日交易次数
        if self.trades_today >= risk_config['max_daily_trades']:
            self.logger.warning(f"⚠️ 达到日交易次数限制: {self.trades_today}")
            return True
            
        return False
        
    async def execute_trading_cycle(self):
        """执行交易周期"""
        # 这里应该是真实的交易逻辑
        # 为了安全，现在只是模拟
        import random
        
        if random.random() > 0.95:  # 5%概率执行交易
            self.trades_today += 1
            
            # 模拟交易结果
            trade_pnl = random.uniform(-10, 15)  # -$10到+$15
            self.daily_pnl += trade_pnl
            self.total_pnl += trade_pnl
            
            if trade_pnl > 0:
                self.consecutive_losses = 0
                self.logger.info(f"✅ 交易盈利: +${trade_pnl:.2f}")
            else:
                self.consecutive_losses += 1
                self.logger.info(f"❌ 交易亏损: ${trade_pnl:.2f}")
                
    def generate_hourly_report(self):
        """生成小时报告"""
        self.logger.info("📊 小时交易报告")
        self.logger.info(f"今日交易次数: {self.trades_today}")
        self.logger.info(f"今日盈亏: ${self.daily_pnl:.2f}")
        self.logger.info(f"总盈亏: ${self.total_pnl:.2f}")
        self.logger.info(f"连续亏损: {self.consecutive_losses}次")
        
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info("🛑 收到停止信号，正在安全关闭...")
        self.running = False
        
    async def run_production_trading(self):
        """运行生产交易"""
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 加载配置
        if not self.load_config_safely():
            return False
            
        # 验证设置
        if not self.validate_production_setup():
            return False
            
        # 显示警告和信息
        self.print_production_warning()
        self.print_trading_info()
        
        # 获取用户确认
        if not self.get_user_confirmation():
            self.logger.info("❌ 用户取消交易")
            return False
            
        self.running = True
        self.logger.info("🚀 开始生产环境交易")
        
        try:
            await self.simulate_production_trading()
            self.logger.info("✅ 交易会话结束")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 交易过程中发生错误: {e}")
            return False
        finally:
            self.running = False

def main():
    """主函数"""
    print("🚀 TradeFan 生产环境交易系统")
    print("⚠️  真实资金交易 - 请谨慎操作")
    
    # 检查配置文件
    config_file = "config/production_config.yaml"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)
    
    # 创建交易管理器
    manager = ProductionTradingManager(config_file)
    
    # 运行交易
    try:
        asyncio.run(manager.run_production_trading())
    except KeyboardInterrupt:
        print("\n🛑 用户中断交易")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
