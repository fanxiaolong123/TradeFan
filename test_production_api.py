#!/usr/bin/env python3
"""
生产环境API快速测试
验证真实API连接和账户状态
"""

import os
import sys
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

def test_production_api():
    """测试生产环境API"""
    print("🔧 生产环境API连接测试")
    print("=" * 50)
    
    # 从用户提供的密钥（仅用于测试）
    api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
    api_secret = "QkKb8JjFOhnC0Ri4Zya6HMeBMtuMeArGR9zem38ULwm8Zo6O0sLORNs9OX63rdWv"
    
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-8:]}")
    print(f"🔐 API Secret: {api_secret[:8]}...{api_secret[-8:]}")
    print("🌐 生产环境: https://api.binance.com")
    print("=" * 50)
    
    base_url = "https://api.binance.com"
    
    def generate_signature(query_string: str) -> str:
        return hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    # 1. 测试服务器时间
    print("🕐 测试服务器连接...")
    try:
        response = requests.get(f"{base_url}/api/v3/time", timeout=10)
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            print(f"✅ 服务器时间: {datetime.fromtimestamp(server_time/1000)}")
        else:
            print(f"❌ 服务器连接失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 服务器连接异常: {e}")
        return False
    
    # 2. 测试账户信息
    print("\n👤 测试账户信息...")
    try:
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urlencode(params)
        signature = generate_signature(query_string)
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        response = requests.get(f"{base_url}/api/v3/account", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()
            print(f"✅ 账户类型: {account_data.get('accountType', 'UNKNOWN')}")
            print(f"📊 权限: {', '.join(account_data.get('permissions', []))}")
            
            # 显示余额
            balances = account_data.get('balances', [])
            print("\n💰 账户余额:")
            total_usdt_value = 0
            
            for balance in balances:
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    total = free + locked
                    print(f"  • {balance['asset']}: {total:.8f} (可用: {free:.8f}, 锁定: {locked:.8f})")
                    
                    # 简单估算USDT价值（仅对主要币种）
                    if balance['asset'] == 'USDT':
                        total_usdt_value += total
                    elif balance['asset'] == 'BTC':
                        total_usdt_value += total * 60000  # 粗略估算
                    elif balance['asset'] == 'ETH':
                        total_usdt_value += total * 3000   # 粗略估算
                        
            print(f"\n💵 估算总价值: ~${total_usdt_value:.2f} USDT")
            
            if total_usdt_value >= 500:
                print("✅ 账户资金充足，可以开始交易")
            else:
                print("⚠️ 账户资金不足$500，请充值后再交易")
                
        else:
            print(f"❌ 账户信息获取失败: {response.status_code}")
            if response.text:
                try:
                    error_data = response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"错误详情: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 账户信息获取异常: {e}")
        return False
    
    # 3. 测试交易权限
    print("\n🔐 测试交易权限...")
    try:
        # 测试获取交易状态
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urlencode(params)
        signature = generate_signature(query_string)
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        response = requests.get(f"{base_url}/api/v3/account/status", headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ 账户状态: {status_data.get('data', 'Normal')}")
        else:
            print(f"⚠️ 交易状态检查: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ 交易权限检查异常: {e}")
    
    # 4. 测试市场数据
    print("\n📊 测试市场数据...")
    try:
        response = requests.get(f"{base_url}/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=10)
        if response.status_code == 200:
            ticker = response.json()
            print(f"✅ BTCUSDT 当前价格: ${float(ticker['lastPrice']):,.2f}")
            print(f"📈 24h变化: {float(ticker['priceChangePercent']):.2f}%")
        else:
            print(f"❌ 市场数据获取失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 市场数据获取异常: {e}")
    
    print("\n" + "=" * 50)
    print("✅ 生产环境API测试完成")
    print("💡 如果所有测试通过，可以开始交易")
    print("⚠️ 请确保设置合理的风险参数")
    
    return True

if __name__ == "__main__":
    test_production_api()
