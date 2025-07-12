#!/usr/bin/env python3
"""
TradeFan 生产环境监控面板
专门监控实际交易的实时状态
"""

import os
import sys
import json
import time
import requests
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlencode
import yaml

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ProductionMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.api_key = self.config['api']['api_key']
        self.api_secret = self.config['api']['api_secret']
        self.base_url = self.config['api']['base_url']
        
    def load_config(self):
        """加载生产配置"""
        config_path = "config/live_production_config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            return {}
    
    def create_signature(self, params: dict) -> str:
        """创建API签名"""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def make_request(self, endpoint: str, params: dict = None) -> dict:
        """发送API请求"""
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self.create_signature(params)
        
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API请求失败: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return {}
    
    def get_account_info(self) -> dict:
        """获取账户信息"""
        return self.make_request("/api/v3/account")
    
    def get_open_orders(self) -> list:
        """获取当前挂单"""
        return self.make_request("/api/v3/openOrders")
    
    def get_recent_trades(self, symbol: str = "BTCUSDT", limit: int = 10) -> list:
        """获取最近交易"""
        params = {"symbol": symbol, "limit": limit}
        return self.make_request("/api/v3/myTrades", params)
    
    def get_24hr_stats(self, symbol: str) -> dict:
        """获取24小时统计"""
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            response = requests.get(url, params={"symbol": symbol}, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    def check_trading_status(self):
        """检查交易状态"""
        print("🔍 检查生产环境交易状态...")
        print("=" * 50)
        
        # 1. 账户信息
        print("📊 账户信息:")
        account = self.get_account_info()
        if account:
            print(f"   账户类型: {account.get('accountType', 'N/A')}")
            print(f"   交易权限: {account.get('permissions', [])}")
            
            # 余额信息
            balances = account.get('balances', [])
            usdt_balance = 0
            btc_balance = 0
            eth_balance = 0
            
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    if asset == 'USDT':
                        usdt_balance = total
                        print(f"   💰 USDT: {total:.2f} (可用: {free:.2f}, 冻结: {locked:.2f})")
                    elif asset == 'BTC':
                        btc_balance = total
                        print(f"   ₿ BTC: {total:.6f} (可用: {free:.6f}, 冻结: {locked:.6f})")
                    elif asset == 'ETH':
                        eth_balance = total
                        print(f"   Ξ ETH: {total:.6f} (可用: {free:.6f}, 冻结: {locked:.6f})")
        else:
            print("   ❌ 无法获取账户信息")
        
        print()
        
        # 2. 当前挂单
        print("📋 当前挂单:")
        open_orders = self.get_open_orders()
        if open_orders:
            for order in open_orders:
                print(f"   🔸 {order['symbol']}: {order['side']} {order['origQty']} @ {order['price']}")
                print(f"      状态: {order['status']}, 时间: {datetime.fromtimestamp(order['time']/1000)}")
        else:
            print("   ✅ 当前无挂单")
        
        print()
        
        # 3. 最近交易
        print("📈 最近交易记录:")
        symbols = ['BTCUSDT', 'ETHUSDT']
        total_trades_today = 0
        total_pnl_today = 0
        
        for symbol in symbols:
            trades = self.get_recent_trades(symbol, 5)
            if trades:
                print(f"   {symbol}:")
                for trade in trades[-3:]:  # 显示最近3笔
                    trade_time = datetime.fromtimestamp(trade['time']/1000)
                    side = "买入" if trade['isBuyer'] else "卖出"
                    print(f"     {trade_time.strftime('%H:%M:%S')} - {side} {trade['qty']} @ ${float(trade['price']):.2f}")
                    
                    # 统计今日交易
                    if trade_time.date() == datetime.now().date():
                        total_trades_today += 1
        
        print()
        
        # 4. 市场价格
        print("💹 当前市场价格:")
        for symbol in symbols:
            stats = self.get_24hr_stats(symbol)
            if stats:
                price = float(stats['lastPrice'])
                change = float(stats['priceChangePercent'])
                volume = float(stats['volume'])
                print(f"   {symbol}: ${price:.2f} ({change:+.2f}%) 24h成交量: {volume:.0f}")
        
        print()
        
        # 5. 交易系统状态
        print("🔧 交易系统状态:")
        
        # 检查进程
        import subprocess
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if 'start_live_trading.py' in result.stdout:
                print("   ✅ 实时交易进程正在运行")
            else:
                print("   ❌ 实时交易进程未运行")
        except:
            print("   ⚠️ 无法检查进程状态")
        
        # 检查日志文件
        log_dir = "logs/live_trading"
        if os.path.exists(log_dir):
            log_files = os.listdir(log_dir)
            if log_files:
                latest_log = max(log_files)
                log_path = os.path.join(log_dir, latest_log)
                log_size = os.path.getsize(log_path)
                print(f"   📝 最新日志: {latest_log} ({log_size} bytes)")
            else:
                print("   ⚠️ 无日志文件")
        else:
            print("   ❌ 日志目录不存在")
        
        print()
        print("=" * 50)
        print(f"📊 监控完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def start_continuous_monitoring(self):
        """启动连续监控"""
        print("🚀 启动生产环境连续监控...")
        print("💡 按 Ctrl+C 停止监控")
        print()
        
        try:
            while True:
                self.check_trading_status()
                print("\n⏰ 等待60秒后下次检查...\n")
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n⚠️ 监控被用户中断")


def main():
    """主函数"""
    print("🎯 TradeFan 生产环境监控")
    print("=" * 40)
    
    monitor = ProductionMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        monitor.start_continuous_monitoring()
    else:
        monitor.check_trading_status()


if __name__ == "__main__":
    main()
