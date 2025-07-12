#!/usr/bin/env python3
"""
快速Binance连接测试
验证API密钥是否正确配置
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.binance_connector import BinanceConnector


async def quick_test():
    """快速连接测试"""
    print("🔗 Binance API 连接测试")
    print("=" * 30)
    
    # 获取API密钥
    api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    print(f"📋 API Key: {api_key[:10]}...{api_key[-10:]}")
    
    if not api_secret:
        print("❌ 请先设置API Secret:")
        print("   export BINANCE_API_SECRET=\"your_actual_secret\"")
        return False
    
    print(f"📋 API Secret: {'*' * 20} (已设置)")
    
    try:
        # 测试连接 (使用测试网)
        async with BinanceConnector(api_key, api_secret, testnet=True) as connector:
            print("\n🧪 测试连接...")
            
            # 连接测试
            if await connector.test_connectivity():
                print("   ✅ 连接成功")
            else:
                print("   ❌ 连接失败")
                return False
            
            # 获取账户信息
            try:
                account = await connector.get_account_info()
                print("   ✅ 账户验证成功")
                
                # 检查余额
                balances = await connector.get_balance()
                usdt_balance = balances.get('USDT', {}).get('free', 0)
                
                if usdt_balance > 0:
                    print(f"   💰 USDT余额: {usdt_balance}")
                    print("   ✅ 可以开始交易")
                else:
                    print("   ⚠️ 测试网余额为0")
                    print("   💡 请访问 https://testnet.binance.vision/ 获取测试币")
                
            except Exception as e:
                print(f"   ❌ 账户验证失败: {e}")
                return False
            
            # 测试价格获取
            try:
                btc_price = await connector.get_symbol_price('BTCUSDT')
                print(f"   📊 BTC价格: ${btc_price:,.2f}")
            except Exception as e:
                print(f"   ⚠️ 价格获取警告: {e}")
            
            print("\n🎉 连接测试完成！系统已准备就绪")
            return True
            
    except Exception as e:
        print(f"\n❌ 连接测试失败: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(quick_test())
        if success:
            print("\n🚀 可以开始6小时测试交易了！")
            print("   命令: python3 start_6hour_trading.py")
        else:
            print("\n🔧 请修复连接问题后重试")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被中断")
        sys.exit(0)
