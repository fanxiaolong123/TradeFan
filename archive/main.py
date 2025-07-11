"""
自动交易系统主程序
整合所有模块，提供统一的入口点
"""

import sys
import os
import argparse
from typing import Dict, List

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils import ConfigLoader
from modules.log_module import LogModule
from modules.data_module import DataModule
from modules.strategy_module import StrategyManager, TrendFollowingStrategy
from modules.risk_control_module import RiskControlModule
from modules.execution_module import ExecutionModule
from modules.backtest_module import BacktestModule
from modules.monitor_module import MonitorModule

class TradingSystem:
    """自动交易系统主类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化交易系统"""
        try:
            # 加载配置
            self.config_loader = ConfigLoader(config_path)
            self.config = self.config_loader.config
            
            # 初始化日志模块
            self.logger = LogModule(self.config)
            self.logger.log_system_status("系统初始化", "开始初始化交易系统")
            
            # 初始化各个模块
            self._init_modules()
            
            # 初始化策略
            self._init_strategies()
            
            self.logger.log_system_status("系统初始化", "交易系统初始化完成")
            
        except Exception as e:
            print(f"系统初始化失败: {e}")
            sys.exit(1)
    
    def _init_modules(self):
        """初始化各个模块"""
        try:
            # 数据模块
            self.data_module = DataModule(self.config, self.logger)
            
            # 风险控制模块
            self.risk_control = RiskControlModule(self.config, self.logger)
            
            # 执行模块
            self.execution_module = ExecutionModule(self.config, self.data_module, self.logger)
            
            # 策略管理器
            self.strategy_manager = StrategyManager(self.logger)
            
            # 回测模块
            self.backtest_module = BacktestModule(
                self.config, self.data_module, self.strategy_manager,
                self.risk_control, self.execution_module, self.logger
            )
            
            # 监控模块
            self.monitor_module = MonitorModule(
                self.config, self.risk_control, self.data_module, self.logger
            )
            
        except Exception as e:
            raise Exception(f"模块初始化失败: {e}")
    
    def _init_strategies(self):
        """初始化策略"""
        try:
            # 获取策略配置
            strategy_config = self.config.get('strategy', {})
            strategy_name = strategy_config.get('name', 'TrendFollowing')
            
            # 为每个币种创建策略实例
            symbols = self.config_loader.get_symbols()
            
            for symbol_config in symbols:
                symbol = symbol_config['symbol']
                strategy_params = symbol_config.get('strategy_params', {})
                
                # 创建策略实例
                if strategy_name == 'TrendFollowing':
                    strategy = TrendFollowingStrategy(strategy_params, self.logger)
                    self.strategy_manager.add_strategy(f"{strategy_name}_{symbol}", strategy)
                
                self.logger.info(f"为{symbol}创建{strategy_name}策略")
            
            # 创建默认策略
            default_params = {
                'fast_ma': 20,
                'slow_ma': 50,
                'adx_period': 14,
                'adx_threshold': 25,
                'donchian_period': 20
            }
            default_strategy = TrendFollowingStrategy(default_params, self.logger)
            self.strategy_manager.add_strategy('TrendFollowing', default_strategy)
            
        except Exception as e:
            raise Exception(f"策略初始化失败: {e}")
    
    def run_backtest(self, symbols: List[str] = None, strategy_name: str = None) -> Dict:
        """运行回测"""
        try:
            if symbols is None:
                symbol_configs = self.config_loader.get_symbols()
                symbols = [config['symbol'] for config in symbol_configs]
            
            if strategy_name is None:
                strategy_name = 'TrendFollowing'
            
            self.logger.info(f"开始回测 - 币种: {symbols}, 策略: {strategy_name}")
            
            # 运行回测
            results = self.backtest_module.run_backtest(symbols, strategy_name)
            
            return results
            
        except Exception as e:
            self.logger.error(f"回测执行失败: {e}")
            return {}
    
    def run_live_trading(self):
        """运行实盘交易"""
        try:
            self.logger.info("开始实盘交易模式")
            
            # 验证API连接
            self._validate_api_connection()
            
            # 启动监控
            self.monitor_module.start_monitoring()
            
            # 获取交易币种
            symbol_configs = self.config_loader.get_symbols()
            
            self.logger.info("实盘交易系统运行中...")
            self.logger.info("按 Ctrl+C 停止交易")
            
            try:
                while True:
                    # 主交易循环
                    self._trading_loop(symbol_configs)
                    
                    # 等待下次循环
                    import time
                    time.sleep(60)  # 每分钟执行一次
                    
            except KeyboardInterrupt:
                self.logger.info("收到停止信号，正在关闭系统...")
                self._shutdown()
                
        except Exception as e:
            self.logger.error(f"实盘交易失败: {e}")
            self._shutdown()
    
    def _validate_api_connection(self):
        """验证API连接"""
        try:
            # 测试获取账户余额
            balance = self.data_module.get_account_balance()
            if balance:
                self.logger.info("API连接验证成功")
            else:
                raise Exception("无法获取账户信息")
                
        except Exception as e:
            raise Exception(f"API连接验证失败: {e}")
    
    def _trading_loop(self, symbol_configs: List[Dict]):
        """主交易循环"""
        try:
            for symbol_config in symbol_configs:
                symbol = symbol_config['symbol']
                
                try:
                    # 获取最新数据
                    timeframe = self.config.get('strategy', {}).get('timeframe', '1h')
                    lookback = self.config.get('strategy', {}).get('lookback_period', 200)
                    
                    data = self.data_module.get_ohlcv(symbol, timeframe, lookback)
                    
                    if data.empty or len(data) < 50:
                        self.logger.debug(f"{symbol}数据不足，跳过")
                        continue
                    
                    # 获取策略
                    strategy_key = f"TrendFollowing_{symbol}"
                    strategy = self.strategy_manager.get_strategy(strategy_key)
                    
                    if not strategy:
                        strategy = self.strategy_manager.get_strategy('TrendFollowing')
                    
                    if not strategy:
                        self.logger.warning(f"未找到{symbol}的策略")
                        continue
                    
                    # 生成信号
                    signal, indicators = strategy.get_latest_signal(data)
                    current_price = data['close'].iloc[-1]
                    
                    if signal != 0:
                        self.logger.log_strategy_signal(symbol, 
                                                      "BUY" if signal == 1 else "SELL",
                                                      current_price, indicators)
                        
                        # 处理信号
                        self._process_trading_signal(symbol, signal, current_price, indicators)
                    
                    # 检查止损止盈
                    self._check_stop_orders(symbol, current_price)
                    
                except Exception as e:
                    self.logger.error(f"处理{symbol}交易信号失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"交易循环失败: {e}")
    
    def _process_trading_signal(self, symbol: str, signal: int, current_price: float, 
                              indicators: Dict):
        """处理交易信号"""
        try:
            position = self.risk_control.get_position(symbol)
            
            # 计算信号强度
            signal_strength = 0.5  # 简化处理，可以根据indicators计算
            
            if signal == 1:  # 买入信号
                if position.is_empty() or position.is_short():
                    # 计算仓位大小
                    position_size = self.risk_control.calculate_position_size(
                        symbol, signal_strength, current_price
                    )
                    
                    if position_size > 0:
                        # 风控检查
                        passed, reason, adjusted_size = self.risk_control.check_position_limit(
                            symbol, position_size, current_price
                        )
                        
                        if passed:
                            # 创建买入订单
                            order = self.execution_module.create_order(
                                symbol, "buy", adjusted_size, current_price, "market"
                            )
                            
                            # 执行订单
                            if self.execution_module.execute_order(order):
                                # 更新持仓
                                self.risk_control.update_position(
                                    symbol, "buy", order.filled_amount, order.filled_price
                                )
                                
                                # 记录日志
                                self.logger.log_order(order, "filled")
                        else:
                            self.logger.log_risk_control(symbol, "拒绝买入", reason)
            
            elif signal == -1:  # 卖出信号
                if position.is_long():
                    # 平多仓
                    order = self.execution_module.create_order(
                        symbol, "sell", position.size, current_price, "market"
                    )
                    
                    # 执行订单
                    if self.execution_module.execute_order(order):
                        # 更新持仓
                        self.risk_control.update_position(
                            symbol, "sell", order.filled_amount, order.filled_price
                        )
                        
                        # 记录日志
                        self.logger.log_order(order, "filled")
                        
        except Exception as e:
            self.logger.error(f"处理{symbol}交易信号失败: {e}")
    
    def _check_stop_orders(self, symbol: str, current_price: float):
        """检查止损止盈订单"""
        try:
            stop_orders = self.risk_control.check_stop_loss_take_profit(symbol, current_price)
            
            for stop_order in stop_orders:
                # 创建止损止盈订单
                order = self.execution_module.create_order(
                    stop_order['symbol'],
                    stop_order['side'],
                    stop_order['amount'],
                    stop_order['price'],
                    "market"
                )
                
                # 执行订单
                if self.execution_module.execute_order(order):
                    # 更新持仓
                    self.risk_control.update_position(
                        symbol, stop_order['side'], order.filled_amount, order.filled_price
                    )
                    
                    # 记录日志
                    self.logger.log_order(order, "filled")
                    self.logger.log_risk_control(symbol, "止损止盈触发", stop_order['reason'])
                    
        except Exception as e:
            self.logger.error(f"检查{symbol}止损止盈失败: {e}")
    
    def _shutdown(self):
        """关闭系统"""
        try:
            self.logger.info("正在关闭交易系统...")
            
            # 停止监控
            self.monitor_module.stop_monitoring()
            
            # 取消所有待处理订单
            pending_orders = self.execution_module.get_pending_orders()
            for order in pending_orders:
                self.execution_module.cancel_order(order.order_id)
            
            # 输出最终状态
            portfolio_status = self.risk_control.get_portfolio_status()
            self.logger.info(f"最终资金: {portfolio_status.get('current_capital', 0):,.2f} USDT")
            self.logger.info(f"总收益率: {portfolio_status.get('total_return', 0):.2%}")
            
            self.logger.log_system_status("系统关闭", "交易系统已安全关闭")
            
        except Exception as e:
            self.logger.error(f"系统关闭失败: {e}")
    
    def get_system_status(self) -> Dict:
        """获取系统状态"""
        try:
            portfolio_status = self.risk_control.get_portfolio_status()
            execution_stats = self.execution_module.get_execution_statistics()
            
            return {
                'portfolio': portfolio_status,
                'execution': execution_stats,
                'last_update': self.monitor_module.last_update,
                'system_uptime': 'N/A'  # 可以添加系统运行时间统计
            }
            
        except Exception as e:
            self.logger.error(f"获取系统状态失败: {e}")
            return {}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动交易系统')
    parser.add_argument('--mode', choices=['backtest', 'live'], default='backtest',
                       help='运行模式: backtest(回测) 或 live(实盘)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='配置文件路径')
    parser.add_argument('--symbols', nargs='+', 
                       help='交易币种列表 (例如: BTC/USDT ETH/USDT)')
    parser.add_argument('--strategy', default='TrendFollowing',
                       help='策略名称')
    
    args = parser.parse_args()
    
    try:
        # 创建交易系统
        trading_system = TradingSystem(args.config)
        
        if args.mode == 'backtest':
            # 回测模式
            print("=" * 60)
            print("运行回测模式")
            print("=" * 60)
            
            symbols = args.symbols
            if not symbols:
                # 使用配置文件中的币种
                symbol_configs = trading_system.config_loader.get_symbols()
                symbols = [config['symbol'] for config in symbol_configs]
            
            results = trading_system.run_backtest(symbols, args.strategy)
            
            if results:
                print("\n回测完成！详细结果请查看日志和生成的图表。")
            else:
                print("\n回测失败，请检查日志。")
                
        elif args.mode == 'live':
            # 实盘模式
            print("=" * 60)
            print("运行实盘交易模式")
            print("警告: 这将使用真实资金进行交易!")
            print("=" * 60)
            
            confirm = input("确认要开始实盘交易吗? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                trading_system.run_live_trading()
            else:
                print("已取消实盘交易")
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
