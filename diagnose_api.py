#!/usr/bin/env python3
"""
详细的API诊断脚本
检查API密钥的具体问题
"""

import os
import sys
import time
import hmac
import hashlib
import requests
import json
from urllib.parse import urlencode
from datetime import datetime

class DetailedAPITest:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://testnet.binance.vision"
        
    def _generate_signature(self, query_string: str) -> str:
        """生成签名"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
    def detailed_account_test(self):
        """详细的账户测试"""
        print("🔍 详细账户信息诊断")
        print("-" * 40)
        
        # 准备请求参数
        timestamp = int(time.time() * 1000)
        params = {'timestamp': timestamp}
        query_string = urlencode(params)
        signature = self._generate_signature(query_string)
        params['signature'] = signature
        
        url = f"{self.base_url}/api/v3/account"
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        print(f"📡 请求URL: {url}")
        print(f"🔑 API Key: {self.api_key[:8]}...{self.api_key[-8:]}")
        print(f"⏰ 时间戳: {timestamp}")
        print(f"📝 查询字符串: {query_string}")
        print(f"🔐 签名: {signature[:16]}...{signature[-16:]}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            print(f"\n📊 响应状态码: {response.status_code}")
            print(f"📋 响应头: {dict(response.headers)}")
            
            if response.text:
                try:
                    response_data = response.json()
                    print(f"📄 响应内容: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📄 响应内容 (原始): {response.text}")
            else:
                print("📄 响应内容: 空")
                
            # 分析错误
            if response.status_code == 401:
                print("\n❌ 401 未授权错误分析:")
                print("  • 可能原因1: API密钥无效")
                print("  • 可能原因2: 签名计算错误")
                print("  • 可能原因3: 时间戳问题")
                print("  • 可能原因4: API密钥权限不足")
                
            elif response.status_code == 403:
                print("\n❌ 403 禁止访问错误分析:")
                print("  • 可能原因1: API密钥被禁用")
                print("  • 可能原因2: IP地址限制")
                print("  • 可能原因3: 请求频率限制")
                
            elif response.status_code == 400:
                print("\n❌ 400 请求错误分析:")
                print("  • 可能原因1: 参数格式错误")
                print("  • 可能原因2: 签名格式错误")
                
        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            
    def test_api_key_permissions(self):
        """测试API密钥权限"""
        print("\n🔐 API密钥权限测试")
        print("-" * 40)
        
        # 测试不需要签名的端点
        endpoints_no_auth = [
            ("/api/v3/ping", "Ping测试"),
            ("/api/v3/time", "服务器时间"),
            ("/api/v3/exchangeInfo", "交易所信息")
        ]
        
        for endpoint, description in endpoints_no_auth:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                status = "✅" if response.status_code == 200 else "❌"
                print(f"{status} {description}: {response.status_code}")
            except Exception as e:
                print(f"❌ {description}: 异常 - {e}")
        
        # 测试需要API密钥但不需要签名的端点
        headers = {'X-MBX-APIKEY': self.api_key}
        endpoints_api_key = [
            ("/api/v3/account/status", "账户状态"),
            ("/api/v3/account/apiTradingStatus", "API交易状态")
        ]
        
        print("\n需要API密钥的端点:")
        for endpoint, description in endpoints_api_key:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5)
                status = "✅" if response.status_code == 200 else "❌"
                print(f"{status} {description}: {response.status_code}")
                if response.status_code != 200 and response.text:
                    try:
                        error_data = response.json()
                        print(f"    错误: {error_data}")
                    except:
                        print(f"    错误: {response.text}")
            except Exception as e:
                print(f"❌ {description}: 异常 - {e}")
                
    def test_signature_generation(self):
        """测试签名生成"""
        print("\n🔐 签名生成测试")
        print("-" * 40)
        
        # 使用官方示例进行测试
        test_cases = [
            {
                'params': 'symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559',
                'expected_signature': 'c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"测试用例 {i+1}:")
            print(f"  参数: {test_case['params']}")
            
            # 使用测试密钥生成签名
            test_secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
            signature = hmac.new(
                test_secret.encode('utf-8'),
                test_case['params'].encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            print(f"  生成签名: {signature}")
            print(f"  期望签名: {test_case['expected_signature']}")
            print(f"  结果: {'✅ 匹配' if signature == test_case['expected_signature'] else '❌ 不匹配'}")
            
        # 测试当前API密钥的签名
        print(f"\n当前API密钥签名测试:")
        test_params = f"timestamp={int(time.time() * 1000)}"
        current_signature = self._generate_signature(test_params)
        print(f"  参数: {test_params}")
        print(f"  签名: {current_signature}")
        print(f"  签名长度: {len(current_signature)} (应该是64)")
        
    def check_testnet_account_status(self):
        """检查测试网络账户状态"""
        print("\n🌐 测试网络账户状态检查")
        print("-" * 40)
        
        print("📋 测试网络账户检查清单:")
        print("1. ✅ API密钥格式正确 (64字符)")
        print("2. ✅ API私钥格式正确 (64字符)")
        print("3. ❓ 测试网络账户是否已激活")
        print("4. ❓ API密钥权限是否正确设置")
        print("5. ❓ 测试网络是否有初始资金")
        
        print("\n💡 建议检查步骤:")
        print("1. 登录 https://testnet.binance.vision")
        print("2. 检查账户是否有测试资金")
        print("3. 确认API密钥权限包含 'Spot & Margin Trading'")
        print("4. 检查API密钥是否启用")
        print("5. 确认没有IP限制或已添加当前IP")

def main():
    """主函数"""
    print("🔧 TradeFan API详细诊断")
    print("=" * 50)
    
    api_key = "36435953f329745c711efa0440f19e95d264b1298cc0c1f2d2241f4c92f69209"
    api_secret = "19ebb309301c2127b39f68591b685d97d76e2d89142c21694c660e1c73334a6c"
    
    tester = DetailedAPITest(api_key, api_secret)
    
    # 运行所有诊断测试
    tester.test_api_key_permissions()
    tester.test_signature_generation()
    tester.detailed_account_test()
    tester.check_testnet_account_status()
    
    print("\n" + "=" * 50)
    print("📋 诊断完成")
    print("💡 如果账户信息仍然无法获取，请:")
    print("   1. 确认测试网络账户已激活并有资金")
    print("   2. 检查API密钥权限设置")
    print("   3. 尝试重新生成API密钥")

if __name__ == "__main__":
    main()
