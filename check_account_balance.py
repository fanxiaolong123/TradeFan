#!/usr/bin/env python3
"""
账户余额检查和充值提醒脚本
"""

import os
import sys
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

def check_account_balance():
    """检查账户余额并提供建议"""
    print("💰 TradeFan 账户余额检查")
    print("=" * 50)
    
    # API凭证（注意：这些密钥已暴露，建议重新生成）
    api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
    api_secret = "QkKb8JjFOhnC0Ri4Zya6HMeBMtuMeArGR9zem38ULwm8Zo6O0sLORNs9OX63rdWv"
    base_url = "https://api.binance.com"
    
    def generate_signature(query_string: str) -> str:
        return hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    try:
        # 获取账户信息
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urlencode(params)
        signature = generate_signature(query_string)
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        response = requests.get(f"{base_url}/api/v3/account", headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ 无法获取账户信息: {response.status_code}")
            return False
            
        account_data = response.json()
        balances = account_data.get('balances', [])
        
        # 获取当前价格
        price_response = requests.get(f"{base_url}/api/v3/ticker/price", timeout=10)
        prices = {item['symbol']: float(item['price']) for item in price_response.json()}
        
        print("📊 当前账户余额详情:")
        print("-" * 30)
        
        total_usdt_value = 0
        significant_balances = []
        
        for balance in balances:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                asset = balance['asset']
                usdt_value = 0
                
                # 计算USDT价值
                if asset == 'USDT':
                    usdt_value = total
                elif asset == 'USDC':
                    usdt_value = total  # 假设1:1
                elif asset == 'BTC':
                    btc_price = prices.get('BTCUSDT', 60000)
                    usdt_value = total * btc_price
                elif asset == 'ETH':
                    eth_price = prices.get('ETHUSDT', 3000)
                    usdt_value = total * eth_price
                elif asset == 'BNB':
                    bnb_price = prices.get('BNBUSDT', 600)
                    usdt_value = total * bnb_price
                else:
                    # 尝试获取其他币种价格
                    symbol = f"{asset}USDT"
                    if symbol in prices:
                        usdt_value = total * prices[symbol]
                
                if usdt_value > 0.01:  # 只显示价值超过1分的资产
                    significant_balances.append({
                        'asset': asset,
                        'total': total,
                        'free': free,
                        'locked': locked,
                        'usdt_value': usdt_value
                    })
                    total_usdt_value += usdt_value
        
        # 按价值排序
        significant_balances.sort(key=lambda x: x['usdt_value'], reverse=True)
        
        for balance in significant_balances:
            print(f"• {balance['asset']}: {balance['total']:.8f} (≈ ${balance['usdt_value']:.2f})")
            if balance['locked'] > 0:
                print(f"  └─ 可用: {balance['free']:.8f}, 锁定: {balance['locked']:.8f}")
        
        print("-" * 30)
        print(f"💵 总估算价值: ${total_usdt_value:.2f}")
        
        # 分析和建议
        print("\n📋 账户分析:")
        if total_usdt_value < 100:
            print("❌ 资金严重不足 - 无法进行有效交易")
            print("💡 建议充值至少 $500 开始交易")
        elif total_usdt_value < 500:
            print("⚠️ 资金不足 - 建议增加资金")
            print(f"💡 当前 ${total_usdt_value:.2f}，建议充值至 $500")
        else:
            print("✅ 资金充足 - 可以开始交易")
            
        # 资金分配建议
        print("\n💡 资金优化建议:")
        usdt_balance = next((b['usdt_value'] for b in significant_balances if b['asset'] == 'USDT'), 0)
        usdc_balance = next((b['usdt_value'] for b in significant_balances if b['asset'] == 'USDC'), 0)
        stable_total = usdt_balance + usdc_balance
        
        if stable_total < total_usdt_value * 0.8:
            print("• 建议将其他代币转换为USDT，便于交易")
            print("• 保持80%以上资金为稳定币（USDT/USDC）")
            
        # 充值指南
        if total_usdt_value < 500:
            print(f"\n📥 充值指南:")
            needed = 500 - total_usdt_value
            print(f"• 需要充值: ${needed:.2f}")
            print("• 推荐充值方式:")
            print("  1. 银行卡购买USDT")
            print("  2. 从其他交易所转入")
            print("  3. P2P交易购买")
            print("• 充值后建议等待1-2个确认再开始交易")
            
        # 安全提醒
        print(f"\n🔐 安全提醒:")
        print("• 您的API密钥已在对话中暴露")
        print("• 强烈建议立即重新生成新的API密钥")
        print("• 设置IP白名单限制API访问")
        print("• 定期检查账户安全设置")
        
        return total_usdt_value >= 500
        
    except Exception as e:
        print(f"❌ 检查账户余额时发生错误: {e}")
        return False

def main():
    """主函数"""
    if check_account_balance():
        print("\n🚀 账户准备就绪，可以开始交易！")
        print("运行命令: python3 start_production_trading.py")
    else:
        print("\n⚠️ 请先充值账户再开始交易")
        print("充值完成后重新运行此脚本检查")

if __name__ == "__main__":
    main()
