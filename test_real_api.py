#!/usr/bin/env python3
"""
Binance 正式环境API连接测试
⚠️ 使用真实API密钥，请谨慎操作
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from modules.binance_connector import BinanceConnector


async def test_real_api():
    """测试真实API连接"""
    print("🔗 Binance 正式环境API测试")
    print("=" * 40)
    print("⚠️  警告：使用真实API密钥")
    print("💡 建议：先小额测试")
    print()
    
    # API密钥配置
    api_key = "Mq0XFmuMRDMBH5NMhFWHGM8ZivVRCvAbqaBXIK3DeJc6EnNj7isN03bpdwTKUKjN"
    api_secret = "QkKb8JjFOhnC0Ri4Zya6HMeBMtuMeArGR9zem38ULwm8Zo6O0sLORNs9OX63rdWv"
    
    print(f"📋 API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"📋 Secret Key: {'*' * 20} (已配置)")
    
    try:
        # 创建连接器 (正式环境)
        async with BinanceConnector(api_key, api_secret, testnet=False) as connector:
            print("\n🔍 正在测试连接...")
            
            # 1. 基础连接测试
            if await connector.test_connectivity():
                print("   ✅ 网络连接正常")
            else:
                print("   ❌ 网络连接失败")
                return False
            
            # 2. 服务器时间同步
            server_time = await connector.get_server_time()
            print(f"   ✅ 服务器时间: {server_time}")
            
            # 3. 账户信息验证
            print("\n💼 账户信息验证...")
            try:
                account_info = await connector.get_account_info()
                print(f"   ✅ 账户类型: {account_info.get('accountType', 'SPOT')}")
                print(f"   ✅ 交易权限: {account_info.get('permissions', [])}")
                print(f"   ✅ 账户状态: {account_info.get('accountStatus', 'NORMAL')}")
                
                # 检查是否可以交易
                can_trade = account_info.get('canTrade', False)
                if can_trade:
                    print("   ✅ 账户可以交易")
                else:
                    print("   ⚠️ 账户交易功能受限")
                
            except Exception as e:
                print(f"   ❌ 账户验证失败: {e}")
                return False
            
            # 4. 余额检查
            print("\n💰 账户余额检查...")
            try:
                balances = await connector.get_balance()
                
                # 显示主要资产余额
                major_assets = ['USDT', 'BTC', 'ETH', 'BNB']
                total_usdt_value = 0
                
                print("   💳 主要资产余额:")
                for asset in major_assets:
                    if asset in balances and balances[asset]['total'] > 0:
                        balance = balances[asset]
                        print(f"      {asset}: {balance['free']:.8f} (可用) + {balance['locked']:.8f} (锁定)")
                        
                        # 估算USDT价值
                        if asset == 'USDT':
                            total_usdt_value += balance['total']
                        elif asset == 'BTC':
                            btc_price = await connector.get_symbol_price('BTCUSDT')
                            total_usdt_value += balance['total'] * btc_price
                        elif asset == 'ETH':
                            eth_price = await connector.get_symbol_price('ETHUSDT')
                            total_usdt_value += balance['total'] * eth_price
                        elif asset == 'BNB':
                            bnb_price = await connector.get_symbol_price('BNBUSDT')
                            total_usdt_value += balance['total'] * bnb_price
                
                print(f"   💰 估算总价值: ~${total_usdt_value:.2f} USDT")
                
                # 安全建议
                if total_usdt_value > 1000:
                    print("   ⚠️ 账户资金较多，建议:")
                    print("      • 先用小额资金测试 ($50-100)")
                    print("      • 设置严格的风险控制")
                    print("      • 密切监控交易表现")
                elif total_usdt_value > 100:
                    print("   💡 建议先用 $50-100 测试系统")
                else:
                    print("   ✅ 资金规模适合测试")
                
            except Exception as e:
                print(f"   ❌ 余额查询失败: {e}")
            
            # 5. 市场数据测试
            print("\n📊 市场数据测试...")
            try:
                btc_price = await connector.get_symbol_price('BTCUSDT')
                eth_price = await connector.get_symbol_price('ETHUSDT')
                bnb_price = await connector.get_symbol_price('BNBUSDT')
                
                print(f"   📈 BTC/USDT: ${btc_price:,.2f}")
                print(f"   📈 ETH/USDT: ${eth_price:,.2f}")
                print(f"   📈 BNB/USDT: ${bnb_price:,.2f}")
                
            except Exception as e:
                print(f"   ⚠️ 市场数据获取警告: {e}")
            
            # 6. 测试下单权限 (仅测试，不实际执行)
            print("\n📋 交易权限测试...")
            try:
                # 测试下单 (test=True，不会实际执行)
                test_result = await connector.place_order(
                    symbol='BTCUSDT',
                    side='BUY',
                    order_type='MARKET',
                    quantity=0.001,
                    test=True  # 重要：仅测试模式
                )
                print("   ✅ 交易权限正常 (测试下单成功)")
                
            except Exception as e:
                print(f"   ⚠️ 交易权限测试: {e}")
            
            print(f"\n🎉 API连接测试完成！")
            print(f"✅ 系统已准备好进行正式环境交易")
            
            # 安全提醒
            print(f"\n🛡️ 安全提醒:")
            print(f"   • 这是正式环境，涉及真实资金")
            print(f"   • 建议从小额开始测试 ($50-100)")
            print(f"   • 设置合理的风险参数")
            print(f"   • 密切监控交易表现")
            print(f"   • 随时可以停止交易")
            
            return True
            
    except Exception as e:
        print(f"\n❌ API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("⚠️  重要提醒：这将使用您的真实Binance账户")
    print("💡 建议：确保您了解风险并准备好开始")
    print()
    
    # 用户确认
    try:
        confirm = input("确认继续测试真实API？(输入 'yes' 继续): ")
        if confirm.lower() != 'yes':
            print("❌ 测试已取消")
            return 1
    except KeyboardInterrupt:
        print("\n❌ 测试已取消")
        return 1
    
    success = await test_real_api()
    
    if success:
        print(f"\n🚀 下一步: 开始小额交易测试")
        print(f"   建议命令: python3 start_small_trading.py --capital 100")
        return 0
    else:
        print(f"\n🔧 请检查API配置或网络连接")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n⚠️ 测试被用户中断")
        sys.exit(0)
