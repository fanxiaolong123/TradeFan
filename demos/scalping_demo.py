#!/usr/bin/env python3
"""
短线交易演示程序
Scalping Trading Demo

展示专业短线交易系统的完整功能：
1. 多时间框架分析
2. 实时信号生成
3. 高频策略执行
4. 风险控制
5. 性能监控
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.scalping_strategy import ScalpingStrategy
from modules.timeframe_analyzer import MultiTimeframeAnalyzer
from modules.realtime_signal_generator import RealTimeSignalGenerator, RealTimeSignal
from modules.data_module import DataModule
from modules.risk_control_module import RiskControlModule

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scalping_demo.log'),
        logging.StreamHandler()
    ]
)

class ScalpingTradingSystem:
    """短线交易系统"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.data_module = DataModule()
        self.risk_control = RiskControlModule()
        self.timeframe_analyzer = MultiTimeframeAnalyzer()
        
        # 初始化策略
        self.scalping_strategy = ScalpingStrategy(
            ema_fast=8,
            ema_medium=21,
            ema_slow=55,
            bb_period=20,
            rsi_period=14,
            volume_threshold=1.5,
            max_risk_per_trade=0.01
        )
        
        # 初始化实时信号生成器
        self.signal_generator = RealTimeSignalGenerator({
            'scalping': self.scalping_strategy
        })
        
        # 交易配置
        self.config = {
            'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
            'timeframes': ['5m', '15m', '30m', '1h'],
            'initial_capital': 10000,
            'max_positions': 3,
            'risk_per_trade': 0.01
        }
        
        # 交易状态
        self.positions = {}
        self.capital = self.config['initial_capital']
        self.trade_history = []
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'start_time': datetime.now()
        }
        
        # 设置信号回调
        self.signal_generator.set_signal_callback(self.handle_signal)
    
    async def start_trading(self):
        """启动交易系统"""
        self.logger.info("启动短线交易系统...")
        
        try:
            # 预加载历史数据
            await self.preload_data()
            
            # 启动实时监控
            await self.signal_generator.start_monitoring(
                self.config['symbols'],
                self.config['timeframes']
            )
            
        except KeyboardInterrupt:
            self.logger.info("用户中断交易系统")
        except Exception as e:
            self.logger.error(f"交易系统异常: {e}")
        finally:
            await self.shutdown()
    
    async def preload_data(self):
        """预加载历史数据"""
        self.logger.info("预加载历史数据...")
        
        for symbol in self.config['symbols']:
            for timeframe in self.config['timeframes']:
                try:
                    # 获取历史数据
                    data = await self.get_historical_data(symbol, timeframe, 200)
                    
                    if not data.empty:
                        # 添加到数据缓冲区
                        for _, row in data.iterrows():
                            market_data = self._create_market_data(symbol, timeframe, row)
                            self.signal_generator.data_buffer.add_data(symbol, timeframe, market_data)
                        
                        self.logger.info(f"加载 {symbol} {timeframe} 数据: {len(data)} 条")
                    
                except Exception as e:
                    self.logger.error(f"加载 {symbol} {timeframe} 数据失败: {e}")
    
    async def get_historical_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """获取历史数据"""
        try:
            # 这里使用模拟数据，实际使用时应该连接真实的数据源
            return self._generate_sample_data(symbol, timeframe, limit)
        except Exception as e:
            self.logger.error(f"获取历史数据失败: {e}")
            return pd.DataFrame()
    
    def _generate_sample_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """生成示例数据"""
        # 基础价格
        base_prices = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
            'BNB/USDT': 300
        }
        
        base_price = base_prices.get(symbol, 1000)
        
        # 时间间隔
        intervals = {
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60
        }
        
        interval_minutes = intervals.get(timeframe, 5)
        
        # 生成数据
        data = []
        current_time = datetime.now() - timedelta(minutes=interval_minutes * limit)
        current_price = base_price
        
        for i in range(limit):
            # 随机价格变动
            price_change = np.random.normal(0, 0.01)  # 1%标准差
            current_price *= (1 + price_change)
            
            # 生成OHLCV
            open_price = current_price * (1 + np.random.normal(0, 0.002))
            high_price = max(open_price, current_price) * (1 + abs(np.random.normal(0, 0.005)))
            low_price = min(open_price, current_price) * (1 - abs(np.random.normal(0, 0.005)))
            close_price = current_price
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': current_time,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
            
            current_time += timedelta(minutes=interval_minutes)
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def _create_market_data(self, symbol: str, timeframe: str, row):
        """创建市场数据对象"""
        from modules.realtime_signal_generator import MarketData
        
        return MarketData(
            symbol=symbol,
            timestamp=row.name,
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            timeframe=timeframe
        )
    
    async def handle_signal(self, signal: RealTimeSignal):
        """处理交易信号"""
        self.logger.info(f"收到信号: {signal.symbol} {signal.timeframe} "
                        f"{'买入' if signal.signal_type == 1 else '卖出'} "
                        f"价格: {signal.entry_price:.4f} 信心度: {signal.confidence:.2f}")
        
        # 多时间框架确认
        confirmation = await self.get_signal_confirmation(signal)
        
        if not confirmation['confirmed']:
            self.logger.info(f"信号未确认: {confirmation['reason']}")
            return
        
        # 风险检查
        risk_check = self.check_risk(signal)
        if not risk_check['approved']:
            self.logger.info(f"风险检查未通过: {risk_check['reason']}")
            return
        
        # 执行交易
        await self.execute_trade(signal, confirmation, risk_check)
    
    async def get_signal_confirmation(self, signal: RealTimeSignal) -> dict:
        """获取信号确认"""
        try:
            # 获取多时间框架数据
            data_dict = {}
            for timeframe in self.config['timeframes']:
                df = self.signal_generator.data_buffer.to_dataframe(
                    signal.symbol, timeframe, 100
                )
                if not df.empty:
                    data_dict[timeframe] = df
            
            if not data_dict:
                return {'confirmed': False, 'reason': '数据不足'}
            
            # 多时间框架分析
            analyses = self.timeframe_analyzer.analyze_all_timeframes(
                signal.symbol, data_dict
            )
            
            # 获取入场确认
            confirmation = self.timeframe_analyzer.get_entry_confirmation(
                analyses, signal.timeframe
            )
            
            return confirmation
            
        except Exception as e:
            self.logger.error(f"信号确认异常: {e}")
            return {'confirmed': False, 'reason': f'确认异常: {e}'}
    
    def check_risk(self, signal: RealTimeSignal) -> dict:
        """风险检查"""
        try:
            # 检查最大持仓数
            if len(self.positions) >= self.config['max_positions']:
                return {'approved': False, 'reason': '达到最大持仓数'}
            
            # 检查资金充足性
            required_capital = signal.entry_price * 0.1  # 假设10%仓位
            if required_capital > self.capital * 0.5:
                return {'approved': False, 'reason': '资金不足'}
            
            # 检查同一交易对持仓
            if signal.symbol in self.positions:
                return {'approved': False, 'reason': '已有该交易对持仓'}
            
            # 检查风险等级
            if signal.risk_level == 'high' and signal.confidence < 0.7:
                return {'approved': False, 'reason': '高风险低信心度'}
            
            return {
                'approved': True,
                'position_size': self.calculate_position_size(signal),
                'max_loss': required_capital * self.config['risk_per_trade']
            }
            
        except Exception as e:
            self.logger.error(f"风险检查异常: {e}")
            return {'approved': False, 'reason': f'风险检查异常: {e}'}
    
    def calculate_position_size(self, signal: RealTimeSignal) -> float:
        """计算仓位大小"""
        # 基于ATR的仓位计算
        risk_amount = self.capital * self.config['risk_per_trade']
        
        # 计算止损距离
        stop_distance = abs(signal.entry_price - signal.stop_loss)
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            max_position = self.capital * 0.2 / signal.entry_price  # 最大20%仓位
            return min(position_size, max_position)
        
        return self.capital * 0.1 / signal.entry_price  # 默认10%仓位
    
    async def execute_trade(self, signal: RealTimeSignal, confirmation: dict, risk_check: dict):
        """执行交易"""
        try:
            position_size = risk_check['position_size']
            
            # 创建持仓记录
            position = {
                'symbol': signal.symbol,
                'side': 'long' if signal.signal_type == 1 else 'short',
                'size': position_size,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'entry_time': signal.timestamp,
                'strategy': signal.metadata.get('strategy', 'unknown'),
                'confidence': signal.confidence,
                'risk_level': signal.risk_level
            }
            
            # 记录持仓
            self.positions[signal.symbol] = position
            
            # 更新资金
            used_capital = position_size * signal.entry_price
            self.capital -= used_capital
            
            self.logger.info(f"执行交易: {signal.symbol} {position['side']} "
                           f"数量: {position_size:.6f} 价格: {signal.entry_price:.4f}")
            
            # 启动持仓监控
            asyncio.create_task(self.monitor_position(signal.symbol))
            
        except Exception as e:
            self.logger.error(f"执行交易异常: {e}")
    
    async def monitor_position(self, symbol: str):
        """监控持仓"""
        while symbol in self.positions:
            try:
                position = self.positions[symbol]
                
                # 获取当前价格
                current_price = await self.get_current_price(symbol)
                
                if current_price is None:
                    await asyncio.sleep(5)
                    continue
                
                # 检查止损止盈
                should_close, reason = self.should_close_position(position, current_price)
                
                if should_close:
                    await self.close_position(symbol, current_price, reason)
                    break
                
                await asyncio.sleep(10)  # 10秒检查一次
                
            except Exception as e:
                self.logger.error(f"监控持仓异常 {symbol}: {e}")
                await asyncio.sleep(30)
    
    async def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            # 从数据缓冲区获取最新价格
            data = self.signal_generator.data_buffer.get_data(symbol, '5m', 1)
            if data:
                return data[-1].close
            return None
        except Exception as e:
            self.logger.error(f"获取当前价格异常: {e}")
            return None
    
    def should_close_position(self, position: dict, current_price: float) -> tuple:
        """判断是否应该平仓"""
        entry_price = position['entry_price']
        side = position['side']
        
        # 计算盈亏
        if side == 'long':
            pnl_ratio = (current_price - entry_price) / entry_price
        else:
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 止损检查
        if side == 'long' and current_price <= position['stop_loss']:
            return True, f"止损触发 (亏损{pnl_ratio:.2%})"
        elif side == 'short' and current_price >= position['stop_loss']:
            return True, f"止损触发 (亏损{pnl_ratio:.2%})"
        
        # 止盈检查
        if side == 'long' and current_price >= position['take_profit']:
            return True, f"止盈触发 (盈利{pnl_ratio:.2%})"
        elif side == 'short' and current_price <= position['take_profit']:
            return True, f"止盈触发 (盈利{pnl_ratio:.2%})"
        
        # 时间止损（持仓超过4小时）
        hold_time = datetime.now() - position['entry_time']
        if hold_time > timedelta(hours=4):
            return True, f"时间止损 (持仓{hold_time})"
        
        return False, ""
    
    async def close_position(self, symbol: str, exit_price: float, reason: str):
        """平仓"""
        try:
            position = self.positions[symbol]
            
            # 计算盈亏
            entry_price = position['entry_price']
            size = position['size']
            side = position['side']
            
            if side == 'long':
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
            
            # 更新资金
            returned_capital = size * exit_price
            self.capital += returned_capital
            
            # 记录交易
            trade_record = {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'size': size,
                'pnl': pnl,
                'pnl_ratio': pnl / (entry_price * size),
                'entry_time': position['entry_time'],
                'exit_time': datetime.now(),
                'hold_time': datetime.now() - position['entry_time'],
                'reason': reason,
                'strategy': position['strategy']
            }
            
            self.trade_history.append(trade_record)
            
            # 更新统计
            self.update_performance_stats(trade_record)
            
            # 移除持仓
            del self.positions[symbol]
            
            self.logger.info(f"平仓: {symbol} {side} 盈亏: {pnl:.2f} ({trade_record['pnl_ratio']:.2%}) 原因: {reason}")
            
        except Exception as e:
            self.logger.error(f"平仓异常: {e}")
    
    def update_performance_stats(self, trade: dict):
        """更新性能统计"""
        self.performance_stats['total_trades'] += 1
        
        if trade['pnl'] > 0:
            self.performance_stats['winning_trades'] += 1
        
        self.performance_stats['total_pnl'] += trade['pnl']
        
        # 计算最大回撤
        current_equity = self.capital + sum(
            pos['size'] * pos['entry_price'] for pos in self.positions.values()
        )
        
        initial_capital = self.config['initial_capital']
        current_drawdown = (initial_capital - current_equity) / initial_capital
        
        if current_drawdown > self.performance_stats['max_drawdown']:
            self.performance_stats['max_drawdown'] = current_drawdown
    
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        total_trades = self.performance_stats['total_trades']
        winning_trades = self.performance_stats['winning_trades']
        
        if total_trades == 0:
            return {'message': '暂无交易记录'}
        
        win_rate = winning_trades / total_trades
        total_pnl = self.performance_stats['total_pnl']
        
        # 计算平均盈利和亏损
        winning_trades_pnl = [t['pnl'] for t in self.trade_history if t['pnl'] > 0]
        losing_trades_pnl = [t['pnl'] for t in self.trade_history if t['pnl'] < 0]
        
        avg_win = np.mean(winning_trades_pnl) if winning_trades_pnl else 0
        avg_loss = np.mean(losing_trades_pnl) if losing_trades_pnl else 0
        
        profit_factor = abs(sum(winning_trades_pnl) / sum(losing_trades_pnl)) if losing_trades_pnl else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.performance_stats['max_drawdown'],
            'current_capital': self.capital,
            'active_positions': len(self.positions),
            'trading_time': datetime.now() - self.performance_stats['start_time']
        }
    
    async def shutdown(self):
        """关闭系统"""
        self.logger.info("关闭交易系统...")
        
        # 停止信号生成器
        self.signal_generator.stop_monitoring()
        
        # 平掉所有持仓
        for symbol in list(self.positions.keys()):
            current_price = await self.get_current_price(symbol)
            if current_price:
                await self.close_position(symbol, current_price, "系统关闭")
        
        # 打印最终报告
        report = self.get_performance_report()
        self.logger.info(f"最终性能报告: {report}")

async def main():
    """主函数"""
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    # 创建交易系统
    trading_system = ScalpingTradingSystem()
    
    print("=" * 60)
    print("短线交易系统演示")
    print("=" * 60)
    print("功能特点:")
    print("1. 多时间框架分析 (5m, 15m, 30m, 1h)")
    print("2. 实时信号生成")
    print("3. 智能风险控制")
    print("4. 动态止损止盈")
    print("5. 性能实时监控")
    print("=" * 60)
    print("按 Ctrl+C 停止系统")
    print("=" * 60)
    
    try:
        # 启动交易系统
        await trading_system.start_trading()
    except KeyboardInterrupt:
        print("\n用户中断，正在关闭系统...")
    except Exception as e:
        print(f"系统异常: {e}")
    finally:
        await trading_system.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
