#!/usr/bin/env python3
"""
TradeFan 基础设施演示程序
展示企业级基础设施的完整功能

运行方式:
python3 demos/infrastructure_demo.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timezone
import random
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.infrastructure_manager import get_infrastructure_manager
from modules.order_management_system import OrderRequest, OrderSide, OrderType
from modules.config_manager import get_config_manager


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InfrastructureDemo:
    """基础设施演示类"""
    
    def __init__(self):
        self.infra = get_infrastructure_manager()
        self.is_running = False
        self.demo_tasks = []
    
    async def run_demo(self):
        """运行完整演示"""
        print("🚀 TradeFan 企业级基础设施演示")
        print("=" * 60)
        
        try:
            # 1. 初始化基础设施
            await self._demo_initialization()
            
            # 2. 演示配置管理
            await self._demo_config_management()
            
            # 3. 演示数据基础设施
            await self._demo_data_infrastructure()
            
            # 4. 演示订单管理系统
            await self._demo_order_management()
            
            # 5. 演示监控系统
            await self._demo_monitoring_system()
            
            # 6. 演示集成功能
            await self._demo_integration()
            
            # 7. 运行实时演示
            await self._demo_realtime_operations()
            
        except KeyboardInterrupt:
            print("\n⚠️  演示被用户中断")
        except Exception as e:
            print(f"❌ 演示过程中出现错误: {e}")
            logger.exception("Demo error")
        finally:
            await self._cleanup()
    
    async def _demo_initialization(self):
        """演示基础设施初始化"""
        print("\n📋 步骤 1: 基础设施初始化")
        print("-" * 40)
        
        print("🔧 正在初始化 TradeFan 基础设施...")
        success = await self.infra.initialize("development")
        
        if success:
            print("✅ 基础设施初始化成功!")
            
            # 显示系统状态
            status = self.infra.get_system_status()
            print(f"   - 环境: {status['environment']}")
            print(f"   - 版本: {status['version']}")
            print(f"   - 启动时间: {status['startup_time']}")
            
            # 健康检查
            health = await self.infra.health_check()
            print("   - 组件健康状态:")
            for component, is_healthy in health.items():
                status_icon = "✅" if is_healthy else "❌"
                print(f"     {status_icon} {component}")
        else:
            print("❌ 基础设施初始化失败!")
            return False
        
        await asyncio.sleep(2)
        return True
    
    async def _demo_config_management(self):
        """演示配置管理"""
        print("\n⚙️  步骤 2: 配置管理演示")
        print("-" * 40)
        
        config_manager = get_config_manager()
        
        # 显示当前配置
        config = config_manager.get_config()
        print(f"📄 当前配置环境: {config.environment}")
        print(f"   - 初始资金: ${config.trading.initial_capital:,.2f}")
        print(f"   - 最大仓位: {config.trading.max_positions}")
        print(f"   - 风险比例: {config.trading.max_risk_per_trade:.1%}")
        
        # 演示配置更新
        print("\n🔄 演示配置热更新...")
        updates = {
            "trading": {
                "initial_capital": 15000.0,
                "max_positions": 5
            }
        }
        
        success = config_manager.update_config(updates)
        if success:
            print("✅ 配置更新成功!")
            updated_config = config_manager.get_config()
            print(f"   - 新的初始资金: ${updated_config.trading.initial_capital:,.2f}")
            print(f"   - 新的最大仓位: {updated_config.trading.max_positions}")
        else:
            print("❌ 配置更新失败!")
        
        await asyncio.sleep(2)
    
    async def _demo_data_infrastructure(self):
        """演示数据基础设施"""
        print("\n💾 步骤 3: 数据基础设施演示")
        print("-" * 40)
        
        # 模拟市场数据
        symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        timeframes = ["1m", "5m", "15m"]
        
        print("📊 存储模拟市场数据...")
        for symbol in symbols:
            for timeframe in timeframes:
                # 生成模拟数据
                base_price = 45000 if "BTC" in symbol else 3000 if "ETH" in symbol else 300
                market_data = {
                    "open": base_price * (1 + random.uniform(-0.01, 0.01)),
                    "high": base_price * (1 + random.uniform(0, 0.02)),
                    "low": base_price * (1 + random.uniform(-0.02, 0)),
                    "close": base_price * (1 + random.uniform(-0.01, 0.01)),
                    "volume": random.uniform(100, 1000),
                    "timestamp": datetime.now(timezone.utc)
                }
                
                await self.infra.store_market_data(symbol, timeframe, market_data)
                
                # 生成技术指标
                indicators = {
                    "ema_fast": market_data["close"] * (1 + random.uniform(-0.005, 0.005)),
                    "ema_slow": market_data["close"] * (1 + random.uniform(-0.01, 0.01)),
                    "rsi": random.uniform(30, 70),
                    "macd": random.uniform(-50, 50),
                    "bb_upper": market_data["close"] * 1.02,
                    "bb_lower": market_data["close"] * 0.98
                }
                
                await self.infra.store_indicators(symbol, timeframe, indicators)
        
        print(f"✅ 已存储 {len(symbols) * len(timeframes)} 组市场数据和指标")
        
        # 演示数据查询
        print("\n🔍 演示数据查询...")
        cached_data = await self.infra.get_market_data("BTC/USDT", "1m")
        if not cached_data.empty:
            print(f"   - 查询到 BTC/USDT 1m 数据: {len(cached_data)} 条记录")
        
        cached_indicators = await self.infra.get_indicators("BTC/USDT", "1m")
        if cached_indicators:
            print(f"   - 查询到技术指标: {list(cached_indicators.keys())}")
        
        await asyncio.sleep(2)
    
    async def _demo_order_management(self):
        """演示订单管理系统"""
        print("\n📋 步骤 4: 订单管理系统演示")
        print("-" * 40)
        
        # 演示不同类型的订单
        order_types = [
            ("市价单", OrderType.MARKET),
            ("限价单", OrderType.LIMIT),
            ("TWAP订单", OrderType.TWAP),
            ("冰山订单", OrderType.ICEBERG)
        ]
        
        submitted_orders = []
        
        for order_name, order_type in order_types:
            print(f"📤 提交{order_name}...")
            
            order_request = OrderRequest(
                symbol="BTC/USDT",
                side=OrderSide.BUY if random.random() > 0.5 else OrderSide.SELL,
                order_type=order_type,
                quantity=random.uniform(0.1, 2.0),
                price=45000.0 if order_type in [OrderType.LIMIT, OrderType.ICEBERG] else None,
                strategy_id="demo_strategy",
                twap_duration=300 if order_type == OrderType.TWAP else None,
                iceberg_qty=0.5 if order_type == OrderType.ICEBERG else None
            )
            
            order = await self.infra.submit_order(order_request)
            if order:
                submitted_orders.append(order)
                print(f"   ✅ {order_name} 提交成功: {order.order_id[:8]}...")
                print(f"      - 交易对: {order.symbol}")
                print(f"      - 方向: {order.side.value}")
                print(f"      - 数量: {order.quantity:.4f}")
                print(f"      - 状态: {order.status.value}")
            else:
                print(f"   ❌ {order_name} 提交失败")
            
            await asyncio.sleep(1)
        
        # 显示订单统计
        if self.infra.order_manager:
            stats = self.infra.order_manager.get_order_statistics()
            print(f"\n📊 订单统计:")
            print(f"   - 总订单数: {stats.get('total_orders', 0)}")
            print(f"   - 成交订单: {stats.get('filled_orders', 0)}")
            print(f"   - 成交率: {stats.get('fill_rate', 0):.1%}")
            print(f"   - 总成交量: {stats.get('total_volume', 0):.4f}")
        
        await asyncio.sleep(2)
    
    async def _demo_monitoring_system(self):
        """演示监控系统"""
        print("\n📊 步骤 5: 监控系统演示")
        print("-" * 40)
        
        if not self.infra.monitoring_system:
            print("❌ 监控系统未初始化")
            return
        
        # 显示监控状态
        monitor_status = self.infra.monitoring_system.get_monitoring_status()
        print(f"📈 监控系统状态:")
        print(f"   - 运行状态: {'✅ 运行中' if monitor_status['is_running'] else '❌ 已停止'}")
        print(f"   - 运行时间: {monitor_status['uptime']:.1f} 秒")
        print(f"   - Prometheus端口: {monitor_status['prometheus_port']}")
        print(f"   - 活跃告警: {monitor_status['active_alerts']}")
        print(f"   - 告警规则: {monitor_status['alert_rules']}")
        
        # 显示告警统计
        alert_stats = self.infra.monitoring_system.alert_manager.get_alert_statistics()
        print(f"\n🚨 告警统计:")
        print(f"   - 总告警数: {alert_stats.get('total_alerts', 0)}")
        print(f"   - 活跃告警: {alert_stats.get('active_alerts', 0)}")
        
        # 显示性能摘要
        perf_summary = self.infra.monitoring_system.performance_monitor.get_performance_summary()
        print(f"\n⚡ 性能摘要:")
        print(f"   - 系统运行时间: {perf_summary['uptime_seconds']:.1f} 秒")
        print(f"   - 总指标数: {perf_summary['total_metrics']}")
        print(f"   - 计时指标: {perf_summary['timer_metrics']}")
        
        print(f"\n🌐 监控访问地址:")
        print(f"   - Prometheus: http://localhost:{monitor_status['prometheus_port']}")
        print(f"   - 指标端点: http://localhost:{monitor_status['prometheus_port']}/metrics")
        
        await asyncio.sleep(2)
    
    async def _demo_integration(self):
        """演示集成功能"""
        print("\n🔗 步骤 6: 集成功能演示")
        print("-" * 40)
        
        print("🔄 演示组件间数据流...")
        
        # 模拟完整的交易流程
        print("   1️⃣ 接收市场数据 → 存储到数据基础设施")
        market_data = {
            "open": 45000.0,
            "high": 45100.0,
            "low": 44900.0,
            "close": 45050.0,
            "volume": 1234.56,
            "timestamp": datetime.now(timezone.utc)
        }
        await self.infra.store_market_data("BTC/USDT", "1m", market_data)
        
        print("   2️⃣ 计算技术指标 → 存储指标数据")
        indicators = {
            "ema_fast": 45025.0,
            "ema_slow": 44980.0,
            "rsi": 65.5,
            "macd": 12.3,
            "signal_strength": 0.75
        }
        await self.infra.store_indicators("BTC/USDT", "1m", indicators)
        
        print("   3️⃣ 生成交易信号 → 提交订单")
        if indicators["signal_strength"] > 0.6:  # 信号强度阈值
            order_request = OrderRequest(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
                strategy_id="integration_demo"
            )
            
            order = await self.infra.submit_order(order_request)
            if order:
                print(f"   4️⃣ 订单提交成功 → 监控系统记录指标")
                print(f"      订单ID: {order.order_id[:8]}...")
        
        print("   5️⃣ 所有操作指标 → 自动记录到监控系统")
        print("✅ 集成功能演示完成!")
        
        await asyncio.sleep(2)
    
    async def _demo_realtime_operations(self):
        """演示实时操作"""
        print("\n⚡ 步骤 7: 实时操作演示 (30秒)")
        print("-" * 40)
        
        print("🔄 启动实时数据模拟...")
        self.is_running = True
        
        # 启动多个并发任务
        self.demo_tasks = [
            asyncio.create_task(self._simulate_market_data()),
            asyncio.create_task(self._simulate_trading_activity()),
            asyncio.create_task(self._monitor_system_health())
        ]
        
        # 运行30秒
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n⚠️  实时演示被中断")
        
        self.is_running = False
        
        # 等待任务完成
        for task in self.demo_tasks:
            task.cancel()
        
        await asyncio.gather(*self.demo_tasks, return_exceptions=True)
        
        print("\n✅ 实时操作演示完成!")
    
    async def _simulate_market_data(self):
        """模拟市场数据流"""
        symbols = ["BTC/USDT", "ETH/USDT"]
        counter = 0
        
        while self.is_running:
            try:
                for symbol in symbols:
                    base_price = 45000 if "BTC" in symbol else 3000
                    
                    # 生成模拟K线数据
                    market_data = {
                        "open": base_price * (1 + random.uniform(-0.005, 0.005)),
                        "high": base_price * (1 + random.uniform(0, 0.01)),
                        "low": base_price * (1 + random.uniform(-0.01, 0)),
                        "close": base_price * (1 + random.uniform(-0.005, 0.005)),
                        "volume": random.uniform(50, 500),
                        "timestamp": datetime.now(timezone.utc)
                    }
                    
                    await self.infra.store_market_data(symbol, "1m", market_data)
                    
                    # 每10次打印一次进度
                    counter += 1
                    if counter % 10 == 0:
                        print(f"📊 已处理 {counter} 条市场数据")
                
                await asyncio.sleep(2)  # 每2秒更新一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Market data simulation error: {e}")
    
    async def _simulate_trading_activity(self):
        """模拟交易活动"""
        order_counter = 0
        
        while self.is_running:
            try:
                # 随机生成订单
                if random.random() < 0.3:  # 30%概率生成订单
                    symbol = random.choice(["BTC/USDT", "ETH/USDT"])
                    side = random.choice([OrderSide.BUY, OrderSide.SELL])
                    
                    order_request = OrderRequest(
                        symbol=symbol,
                        side=side,
                        order_type=OrderType.MARKET,
                        quantity=random.uniform(0.1, 1.0),
                        strategy_id="realtime_demo"
                    )
                    
                    order = await self.infra.submit_order(order_request)
                    if order:
                        order_counter += 1
                        if order_counter % 5 == 0:
                            print(f"📋 已提交 {order_counter} 个订单")
                
                await asyncio.sleep(3)  # 每3秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trading simulation error: {e}")
    
    async def _monitor_system_health(self):
        """监控系统健康状态"""
        check_counter = 0
        
        while self.is_running:
            try:
                health = await self.infra.health_check()
                unhealthy_components = [comp for comp, status in health.items() if not status]
                
                check_counter += 1
                if check_counter % 5 == 0:  # 每5次检查打印一次
                    if unhealthy_components:
                        print(f"⚠️  发现不健康组件: {unhealthy_components}")
                    else:
                        print(f"✅ 系统健康检查通过 (第{check_counter}次)")
                
                await asyncio.sleep(6)  # 每6秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
    
    async def _cleanup(self):
        """清理资源"""
        print("\n🧹 清理资源...")
        
        # 停止演示任务
        self.is_running = False
        for task in self.demo_tasks:
            if not task.done():
                task.cancel()
        
        # 关闭基础设施
        await self.infra.shutdown()
        
        print("✅ 资源清理完成")


async def main():
    """主函数"""
    print("🎯 TradeFan 企业级基础设施完整演示")
    print("📝 本演示将展示以下核心功能:")
    print("   • 基础设施初始化与健康检查")
    print("   • 配置管理与热更新")
    print("   • 高性能数据存储与查询 (InfluxDB + Redis)")
    print("   • 专业订单管理系统 (OMS)")
    print("   • 全栈监控体系 (Prometheus + Grafana)")
    print("   • 组件间无缝集成")
    print("   • 实时数据处理演示")
    print()
    
    input("按 Enter 键开始演示...")
    
    demo = InfrastructureDemo()
    await demo.run_demo()
    
    print("\n🎉 演示完成!")
    print("\n📋 后续步骤:")
    print("   1. 运行 'scripts/deploy.sh -e development -a deploy' 部署完整环境")
    print("   2. 访问 http://localhost:3000 查看 Grafana 监控面板")
    print("   3. 访问 http://localhost:9090 查看 Prometheus 指标")
    print("   4. 查看 logs/ 目录下的详细日志")
    print("\n💡 提示: 这套基础设施支持生产环境部署，具备企业级可靠性!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 演示被用户中断，再见!")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        logger.exception("Demo failed")
