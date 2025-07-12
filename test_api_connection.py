#!/usr/bin/env python3
"""
测试网络API连接验证脚本
验证API密钥是否正常工作
"""

import os
import sys
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

class BinanceTestnetAPI:
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
        
    def _make_request(self, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        if params is None:
            params = {}
            
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)
            
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'status_code': 0,
                'data': {},
                'error': str(e)
            }
    
    def test_server_time(self) -> dict:
        """测试服务器时间"""
        print("🕐 测试服务器时间连接...")
        result = self._make_request("/api/v3/time")
        
        if result['success']:
            server_time = result['data'].get('serverTime', 0)
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            print(f"✅ 服务器时间: {datetime.fromtimestamp(server_time/1000)}")
            print(f"⏰ 本地时间: {datetime.fromtimestamp(local_time/1000)}")
            print(f"⏱️  时间差: {time_diff}ms")
            
            if time_diff > 5000:
                print("⚠️ 警告: 时间差超过5秒，可能影响交易")
        else:
            print(f"❌ 服务器时间获取失败: {result['error']}")
            
        return result
    
    def test_account_info(self) -> dict:
        """测试账户信息"""
        print("\n👤 测试账户信息...")
        result = self._make_request("/api/v3/account", signed=True)
        
        if result['success']:
            account_data = result['data']
            print(f"✅ 账户类型: {account_data.get('accountType', 'UNKNOWN')}")
            print(f"📊 权限: {', '.join(account_data.get('permissions', []))}")
            
            # 显示余额
            balances = account_data.get('balances', [])
            print("\n💰 账户余额:")
            for balance in balances:
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    print(f"  • {balance['asset']}: {free} (可用) + {locked} (锁定)")
                    
        else:
            print(f"❌ 账户信息获取失败: {result['error']}")
            if result['status_code'] == 401:
                print("🔑 可能是API密钥或签名问题")
                
        return result
    
    def test_exchange_info(self) -> dict:
        """测试交易所信息"""
        print("\n🏢 测试交易所信息...")
        result = self._make_request("/api/v3/exchangeInfo")
        
        if result['success']:
            exchange_data = result['data']
            symbols = exchange_data.get('symbols', [])
            
            # 查找我们关心的交易对
            target_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            found_symbols = []
            
            for symbol_info in symbols:
                if symbol_info['symbol'] in target_symbols:
                    found_symbols.append({
                        'symbol': symbol_info['symbol'],
                        'status': symbol_info['status'],
                        'baseAsset': symbol_info['baseAsset'],
                        'quoteAsset': symbol_info['quoteAsset']
                    })
            
            print(f"✅ 交易所状态: {exchange_data.get('timezone', 'UTC')}")
            print("📈 目标交易对状态:")
            for symbol in found_symbols:
                print(f"  • {symbol['symbol']}: {symbol['status']}")
                
        else:
            print(f"❌ 交易所信息获取失败: {result['error']}")
            
        return result
    
    def test_market_data(self) -> dict:
        """测试市场数据"""
        print("\n📊 测试市场数据...")
        result = self._make_request("/api/v3/ticker/24hr", {'symbol': 'BTCUSDT'})
        
        if result['success']:
            ticker = result['data']
            print(f"✅ BTCUSDT 24小时数据:")
            print(f"  • 当前价格: ${float(ticker['lastPrice']):,.2f}")
            print(f"  • 24h变化: {float(ticker['priceChangePercent']):.2f}%")
            print(f"  • 24h成交量: {float(ticker['volume']):,.2f} BTC")
            print(f"  • 24h成交额: ${float(ticker['quoteVolume']):,.2f}")
        else:
            print(f"❌ 市场数据获取失败: {result['error']}")
            
        return result
    
    def test_order_limits(self) -> dict:
        """测试订单限制"""
        print("\n📋 测试订单限制...")
        result = self._make_request("/api/v3/exchangeInfo")
        
        if result['success']:
            symbols = result['data'].get('symbols', [])
            btc_symbol = None
            
            for symbol in symbols:
                if symbol['symbol'] == 'BTCUSDT':
                    btc_symbol = symbol
                    break
            
            if btc_symbol:
                print("✅ BTCUSDT 交易限制:")
                for filter_info in btc_symbol.get('filters', []):
                    if filter_info['filterType'] == 'LOT_SIZE':
                        print(f"  • 最小数量: {filter_info['minQty']}")
                        print(f"  • 最大数量: {filter_info['maxQty']}")
                        print(f"  • 数量步长: {filter_info['stepSize']}")
                    elif filter_info['filterType'] == 'MIN_NOTIONAL':
                        print(f"  • 最小名义价值: ${filter_info['minNotional']}")
        else:
            print(f"❌ 订单限制获取失败: {result['error']}")
            
        return result

def main():
    """主测试函数"""
    print("🔧 TradeFan 测试网络API连接测试")
    print("="*50)
    
    # API凭证
    api_key = "36435953f329745c711efa0440f19e95d264b1298cc0c1f2d2241f4c92f69209"
    api_secret = "19ebb309301c2127b39f68591b685d97d76e2d89142c21694c660e1c73334a6c"
    
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-8:]}")
    print(f"🔐 API Secret: {api_secret[:8]}...{api_secret[-8:]}")
    print("🌐 测试网络: https://testnet.binance.vision")
    print("="*50)
    
    # 创建API客户端
    api = BinanceTestnetAPI(api_key, api_secret)
    
    # 运行测试
    tests = [
        ('服务器连接', api.test_server_time),
        ('账户信息', api.test_account_info),
        ('交易所信息', api.test_exchange_info),
        ('市场数据', api.test_market_data),
        ('订单限制', api.test_order_limits)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result['success']
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results[test_name] = False
    
    # 总结
    print("\n" + "="*50)
    print("📋 测试结果总结:")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n📊 总体结果: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！API连接正常，可以开始交易测试")
        return True
    else:
        print("⚠️ 部分测试失败，请检查API配置或网络连接")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
