#!/usr/bin/env python3
"""
实时交易执行器
基于优化策略的实时交易系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import threading
from modules.enhanced_data_module import EnhancedDataModule

class LiveTradingExecutor:
    """实时交易执行器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        
        # 交易状态
        self.trading_status = {
            'is_running': False,
            'active_positions': {},
            'total_pnl': 0,
            'trade_count': 0,
            'win_count': 0,
            'current_capital': 10000
        }
        
        # 优化策略配置
        self.active_strategies = {
            'PEPE_4H_OPTIMIZED': {
                'symbol': 'PEPE/USDT',
                'timeframe': '4h',
                'name': 'PEPE 4小时优化策略',
                'enabled': True,
                'params': {
                    'ema_fast': 6,
                    'ema_medium': 21,
                    'ema_slow': 55,
                    'rsi_lower': 35,
                    'rsi_upper': 70,
                    'bb_std': 2.2,
                    'stop_loss': 0.02,
                    'take_profit': 0.04,
                    'volume_threshold': 1.5,
                    'position_size': 0.10,
                    'max_hold_hours': 48
                },
                'last_signal_time': None,
                'signal_cooldown': 4 * 3600  # 4小时冷却
            },
            'DOGE_MTF_OPTIMIZED': {
                'symbol': 'DOGE/USDT',
                'timeframe': 'MTF',
                'name': 'DOGE 多时间框架策略',
                'enabled': True,
                'params': {
                    'primary_tf': '4h',
                    'secondary_tf': '1h',
                    'entry_tf': '30m',
                    'signal_threshold': 0.7,
                    'volume_confirmation': 1.5,
                    'position_size': 0.15,
                    'max_hold_hours': 72
                },
                'last_signal_time': None,
                'signal_cooldown': 2 * 3600  # 2小时冷却
            }
        }
        
        # 风险管理
        self.risk_management = {
            'max_daily_loss': 0.05,  # 5%日损失限制
            'max_positions': 3,
            'min_capital_ratio': 0.1,  # 最小资金比例
            'emergency_stop': False
        }
        
        # 交易记录
        self.trade_log = []
        self.performance_log = []
    
    def start_live_trading(self):
        """启动实时交易"""
        print("🚀 启动 TradeFan 实时交易系统")
        print("=" * 60)
        
        # 安全检查
        if not self.pre_trading_checks():
            return
        
        self.trading_status['is_running'] = True
        
        print("✅ 实时交易已启动")
        print("⚠️  注意: 这是模拟交易模式，不会执行真实交易")
        print("\n📊 监控策略:")
        
        for key, strategy in self.active_strategies.items():
            if strategy['enabled']:
                print(f"   ✅ {strategy['name']} ({strategy['symbol']})")
        
        try:
            # 主交易循环
            self.main_trading_loop()
            
        except KeyboardInterrupt:
            print("\n⏹️  交易系统已停止")
            self.stop_live_trading()
        except Exception as e:
            print(f"\n❌ 交易系统错误: {str(e)}")
            self.emergency_stop()
    
    def pre_trading_checks(self) -> bool:
        """交易前检查"""
        print("🔍 执行交易前安全检查...")
        
        checks = []
        
        # 1. 数据连接检查
        try:
            test_data = self.data_module.get_historical_data('BTC/USDT', '1d')
            if not test_data.empty:
                checks.append(("数据连接", True, "✅"))
            else:
                checks.append(("数据连接", False, "❌ 无法获取数据"))
        except Exception as e:
            checks.append(("数据连接", False, f"❌ {str(e)}"))
        
        # 2. 策略配置检查
        valid_strategies = 0
        for key, strategy in self.active_strategies.items():
            if strategy['enabled']:
                valid_strategies += 1
        
        if valid_strategies > 0:
            checks.append(("策略配置", True, f"✅ {valid_strategies}个策略已启用"))
        else:
            checks.append(("策略配置", False, "❌ 没有启用的策略"))
        
        # 3. 风险参数检查
        if self.risk_management['max_daily_loss'] > 0:
            checks.append(("风险控制", True, "✅ 风险参数已设置"))
        else:
            checks.append(("风险控制", False, "❌ 风险参数无效"))
        
        # 4. 资金检查
        if self.trading_status['current_capital'] > 1000:
            checks.append(("资金状态", True, f"✅ ${self.trading_status['current_capital']:,}"))
        else:
            checks.append(("资金状态", False, "❌ 资金不足"))
        
        # 显示检查结果
        print("\n📋 安全检查结果:")
        all_passed = True
        for check_name, passed, message in checks:
            print(f"   {check_name}: {message}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n✅ 所有检查通过，可以开始交易")
            return True
        else:
            print("\n❌ 检查未通过，请解决问题后重试")
            return False
    
    def main_trading_loop(self):
        """主交易循环"""
        loop_count = 0
        
        while self.trading_status['is_running']:
            loop_count += 1
            current_time = datetime.now()
            
            print(f"\n🔄 交易循环 #{loop_count} ({current_time.strftime('%H:%M:%S')})")
            
            # 检查紧急停止
            if self.risk_management['emergency_stop']:
                print("🚨 紧急停止触发")
                break
            
            # 检查每个策略
            for strategy_key, strategy in self.active_strategies.items():
                if not strategy['enabled']:
                    continue
                
                try:
                    self.process_strategy(strategy_key, strategy)
                except Exception as e:
                    print(f"⚠️  策略 {strategy['name']} 处理错误: {str(e)}")
            
            # 更新持仓状态
            self.update_positions()
            
            # 显示当前状态
            self.display_trading_status()
            
            # 风险检查
            if self.check_risk_limits():
                print("🚨 触发风险限制，停止交易")
                break
            
            # 等待下次循环
            print("⏳ 等待下次检查...")
            time.sleep(30)  # 30秒检查一次
            
            # 演示模式：运行10次循环后停止
            if loop_count >= 10:
                print("\n🎯 演示模式完成")
                break
    
    def process_strategy(self, strategy_key: str, strategy: dict):
        """处理单个策略"""
        symbol = strategy['symbol']
        timeframe = strategy['timeframe'] if strategy['timeframe'] != 'MTF' else '30m'
        
        # 获取最新数据
        data = self.data_module.get_historical_data(symbol, timeframe)
        
        if data.empty:
            print(f"   ⚠️  {strategy['name']}: 数据获取失败")
            return
        
        # 计算指标
        data_with_indicators = self.calculate_indicators(data, strategy['params'])
        
        # 生成信号
        signal = self.generate_signal(data_with_indicators, strategy)
        
        current_price = data['close'].iloc[-1]
        
        # 检查是否有该策略的持仓
        position_key = f"{strategy_key}_{symbol.replace('/', '_')}"
        has_position = position_key in self.trading_status['active_positions']
        
        if signal != 0 and not has_position:
            # 新开仓信号
            if self.can_open_position(strategy):
                self.open_position(strategy_key, strategy, signal, current_price)
        elif has_position:
            # 检查平仓条件
            self.check_close_position(strategy_key, strategy, current_price)
        
        # 显示策略状态
        signal_text = "买入" if signal == 1 else "卖出" if signal == -1 else "观望"
        position_text = "持仓中" if has_position else "空仓"
        print(f"   📊 {strategy['name']}: ${current_price:.6f} | {signal_text} | {position_text}")
    
    def calculate_indicators(self, data: pd.DataFrame, params: dict) -> pd.DataFrame:
        """计算技术指标 (简化版)"""
        df = data.copy()
        
        try:
            # EMA
            if 'ema_fast' in params:
                df['ema_fast'] = df['close'].ewm(span=params['ema_fast']).mean()
                df['ema_medium'] = df['close'].ewm(span=params['ema_medium']).mean()
                df['ema_slow'] = df['close'].ewm(span=params['ema_slow']).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # 成交量比率
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14).mean()
            
        except Exception as e:
            print(f"⚠️  指标计算错误: {str(e)}")
        
        return df
    
    def generate_signal(self, data: pd.DataFrame, strategy: dict) -> int:
        """生成交易信号 (简化版)"""
        if len(data) < 50:
            return 0
        
        current = data.iloc[-1]
        params = strategy['params']
        
        try:
            # 基本信号条件
            conditions = []
            
            if 'ema_fast' in params:
                conditions.append(current.get('ema_fast', 0) > current.get('ema_medium', 0))
                conditions.append(current.get('ema_medium', 0) > current.get('ema_slow', 0))
            
            if 'rsi_lower' in params:
                rsi_ok = params['rsi_lower'] < current.get('rsi', 50) < params['rsi_upper']
                conditions.append(rsi_ok)
            
            if 'volume_threshold' in params:
                volume_ok = current.get('volume_ratio', 1) > params['volume_threshold']
                conditions.append(volume_ok)
            
            # 信号强度
            signal_strength = sum(conditions) / len(conditions) if conditions else 0
            
            if signal_strength > 0.7:
                return 1  # 买入
            elif signal_strength < 0.3:
                return -1  # 卖出
            else:
                return 0  # 观望
                
        except Exception as e:
            print(f"⚠️  信号生成错误: {str(e)}")
            return 0
    
    def can_open_position(self, strategy: dict) -> bool:
        """检查是否可以开仓"""
        # 检查最大持仓数
        if len(self.trading_status['active_positions']) >= self.risk_management['max_positions']:
            return False
        
        # 检查资金充足
        required_capital = self.trading_status['current_capital'] * strategy['params']['position_size']
        available_capital = self.trading_status['current_capital'] * 0.8  # 保留20%资金
        
        if required_capital > available_capital:
            return False
        
        # 检查信号冷却时间
        if strategy['last_signal_time']:
            time_since_last = (datetime.now() - strategy['last_signal_time']).total_seconds()
            if time_since_last < strategy['signal_cooldown']:
                return False
        
        return True
    
    def open_position(self, strategy_key: str, strategy: dict, signal: int, price: float):
        """开仓"""
        position_key = f"{strategy_key}_{strategy['symbol'].replace('/', '_')}"
        
        position_size = strategy['params']['position_size']
        position_value = self.trading_status['current_capital'] * position_size
        
        # 计算止损止盈
        if signal == 1:  # 买入
            stop_loss = price * (1 - strategy['params'].get('stop_loss', 0.02))
            take_profit = price * (1 + strategy['params'].get('take_profit', 0.04))
        else:  # 卖出
            stop_loss = price * (1 + strategy['params'].get('stop_loss', 0.02))
            take_profit = price * (1 - strategy['params'].get('take_profit', 0.04))
        
        # 创建持仓记录
        position = {
            'strategy': strategy_key,
            'symbol': strategy['symbol'],
            'direction': signal,
            'entry_price': price,
            'entry_time': datetime.now(),
            'position_size': position_size,
            'position_value': position_value,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'max_hold_time': datetime.now() + timedelta(hours=strategy['params']['max_hold_hours'])
        }
        
        self.trading_status['active_positions'][position_key] = position
        
        # 更新策略状态
        strategy['last_signal_time'] = datetime.now()
        
        # 记录交易
        direction_text = "买入" if signal == 1 else "卖出"
        print(f"   🎯 {strategy['name']}: {direction_text} ${price:.6f}")
        print(f"      止损: ${stop_loss:.6f} | 止盈: ${take_profit:.6f}")
        print(f"      仓位: {position_size*100:.1f}% (${position_value:.2f})")
        
        self.log_trade('OPEN', position)
    
    def check_close_position(self, strategy_key: str, strategy: dict, current_price: float):
        """检查平仓条件"""
        position_key = f"{strategy_key}_{strategy['symbol'].replace('/', '_')}"
        
        if position_key not in self.trading_status['active_positions']:
            return
        
        position = self.trading_status['active_positions'][position_key]
        should_close = False
        close_reason = ""
        
        # 止损止盈检查
        if position['direction'] == 1:  # 多头
            if current_price <= position['stop_loss']:
                should_close = True
                close_reason = "止损"
            elif current_price >= position['take_profit']:
                should_close = True
                close_reason = "止盈"
        else:  # 空头
            if current_price >= position['stop_loss']:
                should_close = True
                close_reason = "止损"
            elif current_price <= position['take_profit']:
                should_close = True
                close_reason = "止盈"
        
        # 时间止损
        if datetime.now() > position['max_hold_time']:
            should_close = True
            close_reason = "超时"
        
        if should_close:
            self.close_position(position_key, current_price, close_reason)
    
    def close_position(self, position_key: str, exit_price: float, reason: str):
        """平仓"""
        position = self.trading_status['active_positions'][position_key]
        
        # 计算盈亏
        if position['direction'] == 1:  # 多头
            pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
        else:  # 空头
            pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
        
        pnl_amount = position['position_value'] * pnl_pct
        
        # 更新资金
        self.trading_status['current_capital'] += pnl_amount
        self.trading_status['total_pnl'] += pnl_amount
        self.trading_status['trade_count'] += 1
        
        if pnl_amount > 0:
            self.trading_status['win_count'] += 1
        
        # 记录平仓
        position['exit_price'] = exit_price
        position['exit_time'] = datetime.now()
        position['pnl_pct'] = pnl_pct * 100
        position['pnl_amount'] = pnl_amount
        position['close_reason'] = reason
        
        # 显示平仓信息
        pnl_text = f"+${pnl_amount:.2f}" if pnl_amount > 0 else f"${pnl_amount:.2f}"
        print(f"   📤 平仓 {position['symbol']}: ${exit_price:.6f} | {reason} | {pnl_text} ({pnl_pct*100:.2f}%)")
        
        # 移除持仓
        del self.trading_status['active_positions'][position_key]
        
        self.log_trade('CLOSE', position)
    
    def update_positions(self):
        """更新持仓状态"""
        if not self.trading_status['active_positions']:
            return
        
        total_unrealized_pnl = 0
        
        for position_key, position in self.trading_status['active_positions'].items():
            # 这里应该获取实时价格，现在用模拟价格
            symbol = position['symbol']
            try:
                data = self.data_module.get_historical_data(symbol, '1h')
                if not data.empty:
                    current_price = data['close'].iloc[-1]
                    
                    # 计算浮动盈亏
                    if position['direction'] == 1:
                        unrealized_pnl = (current_price - position['entry_price']) / position['entry_price']
                    else:
                        unrealized_pnl = (position['entry_price'] - current_price) / position['entry_price']
                    
                    unrealized_pnl *= position['position_value']
                    total_unrealized_pnl += unrealized_pnl
                    
            except Exception as e:
                print(f"⚠️  更新持仓失败 {symbol}: {str(e)}")
        
        # 更新总资产
        self.trading_status['total_equity'] = self.trading_status['current_capital'] + total_unrealized_pnl
    
    def display_trading_status(self):
        """显示交易状态"""
        status = self.trading_status
        
        print(f"\n📊 交易状态:")
        print(f"   当前资金: ${status['current_capital']:,.2f}")
        print(f"   总盈亏: ${status['total_pnl']:,.2f}")
        print(f"   持仓数量: {len(status['active_positions'])}")
        print(f"   交易次数: {status['trade_count']}")
        
        if status['trade_count'] > 0:
            win_rate = status['win_count'] / status['trade_count'] * 100
            print(f"   胜率: {win_rate:.1f}%")
    
    def check_risk_limits(self) -> bool:
        """检查风险限制"""
        # 检查日损失限制
        daily_loss_pct = abs(self.trading_status['total_pnl']) / 10000  # 假设初始资金10000
        
        if daily_loss_pct > self.risk_management['max_daily_loss']:
            print(f"🚨 日损失超限: {daily_loss_pct*100:.2f}% > {self.risk_management['max_daily_loss']*100:.1f}%")
            return True
        
        # 检查最小资金比例
        if self.trading_status['current_capital'] < 10000 * self.risk_management['min_capital_ratio']:
            print(f"🚨 资金不足: ${self.trading_status['current_capital']:,.2f}")
            return True
        
        return False
    
    def log_trade(self, action: str, position: dict):
        """记录交易日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'strategy': position['strategy'],
            'symbol': position['symbol'],
            'direction': position['direction'],
            'price': position.get('exit_price', position['entry_price']),
            'pnl': position.get('pnl_amount', 0),
            'reason': position.get('close_reason', 'OPEN')
        }
        
        self.trade_log.append(log_entry)
        
        # 保存到文件
        try:
            os.makedirs('logs/live_trading', exist_ok=True)
            log_file = f"logs/live_trading/trades_{datetime.now().strftime('%Y%m%d')}.json"
            
            with open(log_file, 'w') as f:
                json.dump(self.trade_log, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  日志保存失败: {str(e)}")
    
    def stop_live_trading(self):
        """停止实时交易"""
        self.trading_status['is_running'] = False
        
        # 平掉所有持仓
        if self.trading_status['active_positions']:
            print("\n📤 平掉所有持仓...")
            for position_key in list(self.trading_status['active_positions'].keys()):
                position = self.trading_status['active_positions'][position_key]
                # 使用当前价格平仓
                try:
                    data = self.data_module.get_historical_data(position['symbol'], '1h')
                    if not data.empty:
                        current_price = data['close'].iloc[-1]
                        self.close_position(position_key, current_price, "系统停止")
                except:
                    pass
        
        # 显示最终统计
        self.display_final_statistics()
    
    def emergency_stop(self):
        """紧急停止"""
        print("🚨 紧急停止交易系统")
        self.risk_management['emergency_stop'] = True
        self.stop_live_trading()
    
    def display_final_statistics(self):
        """显示最终统计"""
        print("\n📊 交易会话统计:")
        print("=" * 40)
        
        status = self.trading_status
        
        print(f"总交易次数: {status['trade_count']}")
        print(f"盈利交易: {status['win_count']}")
        print(f"胜率: {status['win_count']/max(status['trade_count'], 1)*100:.1f}%")
        print(f"总盈亏: ${status['total_pnl']:,.2f}")
        print(f"最终资金: ${status['current_capital']:,.2f}")
        
        if status['total_pnl'] != 0:
            return_pct = status['total_pnl'] / 10000 * 100
            print(f"收益率: {return_pct:.2f}%")


def main():
    """主函数"""
    print("🚀 TradeFan 实时交易执行器")
    print("基于优化策略的专业交易系统")
    print("=" * 50)
    
    executor = LiveTradingExecutor()
    
    print("\n⚠️  重要提示:")
    print("   这是模拟交易系统，不会执行真实交易")
    print("   实际部署前请充分测试和验证")
    
    confirm = input("\n是否启动模拟交易? (y/N): ").strip().lower()
    
    if confirm == 'y':
        executor.start_live_trading()
    else:
        print("👋 交易系统未启动")


if __name__ == "__main__":
    main()
