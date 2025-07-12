#!/usr/bin/env python3
"""
Binance 测试网连接验证脚本
验证API密钥和测试网连接
"""

import asyncio
import os
import sys
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.binance_connector import BinanceConnector


async def test_binance_connection():
    """测试Binance连接"""
    print("🔗 Binance 测试网连接验证")
    print("=" * 40)
    
    # 获取API密钥
    api_key = os.getenv('BINANCE_API_KEY') or "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    print(f"📋 API Key: {api_key[:10]}...{api_key[-10:]}")
    
    if not api_secret:
        print("❌ BINANCE_API_SECRET 环境变量未设置")
        print("💡 请运行: export BINANCE_API_SECRET=\"your_actual_secret\"")
        return False
    
    print(f"📋 API Secret: {'*' * 20} (已设置)")
    
    try:
        # 创建连接器 (强制使用测试网)
        async with BinanceConnector(api_key, api_secret, testnet=True) as connector:
            print("\n🧪 测试连接...")
            
            # 1. 连接测试
            connectivity = await connector.test_connectivity()
            if connectivity:
                print("   ✅ 连接测试通过")
            else:
                print("   ❌ 连接测试失败")
                return False
            
            # 2. 服务器时间
            server_time = await connector.get_server_time()
            print(f"   ✅ 服务器时间: {server_time}")
            
            # 3. 账户信息
            print("\n💰 账户信息...")
            account_info = await connector.get_account_info()
            print(f"   ✅ 账户类型: {account_info.get('accountType', 'Unknown')}")
            print(f"   ✅ 交易权限: {account_info.get('permissions', [])}")
            
            # 4. 余额信息
            print("\n💳 余额信息...")
            balances = await connector.get_balance()
            
            # 显示有余额的资产
            non_zero_balances = {asset: balance for asset, balance in balances.items() 
                               if balance['total'] > 0}
            
            if non_zero_balances:
                print("   💰 可用余额:")
                for asset, balance in non_zero_balances.items():
                    print(f"      {asset}: {balance['free']:.8f} (锁定: {balance['locked']:.8f})")
            else:
                print("   ⚠️ 测试网账户余额为0")
                print("   💡 请访问 https://testnet.binance.vision/ 获取测试币")
            
            # 5. 价格测试
            print("\n📊 价格数据测试...")
            try:
                btc_price = await connector.get_symbol_price('BTCUSDT')
                print(f"   ✅ BTC价格: ${btc_price:,.2f}")
                
                eth_price = await connector.get_symbol_price('ETHUSDT')
                print(f"   ✅ ETH价格: ${eth_price:,.2f}")
                
            except Exception as e:
                print(f"   ⚠️ 价格获取警告: {e}")
            
            # 6. 测试下单 (测试模式)
            print("\n📋 测试下单...")
            try:
                test_order = await connector.place_order(
                    symbol='BTCUSDT',
                    side='BUY',
                    order_type='MARKET',
                    quantity=0.001,
                    test=True  # 测试模式，不会真实下单
                )
                print("   ✅ 测试下单成功 (仅测试，未实际执行)")
                
            except Exception as e:
                print(f"   ⚠️ 测试下单警告: {e}")
            
            print(f"\n🎉 Binance测试网连接验证完成！")
            print(f"✅ 系统已准备好进行测试网交易")
            
            return True
            
    except Exception as e:
        print(f"\n❌ 连接验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)  # 减少日志输出
    
    success = await test_binance_connection()
    
    if success:
        print(f"\n🚀 下一步: 启动测试网交易")
        print(f"   命令: python3 start_testnet_trading.py")
        return 0
    else:
        print(f"\n🔧 请修复连接问题后重试")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(0)
