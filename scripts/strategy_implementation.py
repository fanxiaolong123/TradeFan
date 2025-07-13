#!/usr/bin/env python3
"""
策略实施启动脚本
将优化后的策略投入实际使用
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from modules.enhanced_data_module import EnhancedDataModule

class StrategyImplementation:
    """策略实施管理器"""
    
    def __init__(self):
        self.data_module = EnhancedDataModule()
        
        # 优化后的策略配置
        self.optimized_strategies = {
            'PEPE_4H': {
                'symbol': 'PEPE/USDT',
                'timeframe': '4h',
                'name': 'PEPE 4小时优化策略',
                'expected_return': 32.15,
                'win_rate': 43.7,
                'max_drawdown': 4.48,
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
                    'position_size': 0.10
                }
            },
            'PEPE_30M': {
                'symbol': 'PEPE/USDT',
                'timeframe': '30m',
                'name': 'PEPE 30分钟短线策略',
                'expected_return': 11.06,
                'win_rate': 45.1,
                'max_drawdown': 4.12,
                'params': {
                    'ema_fast': 5,
                    'ema_medium': 18,
                    'ema_slow': 40,
                    'rsi_lower': 25,
                    'rsi_upper': 80,
                    'bb_std': 1.5,
                    'stop_loss': 0.02,
                    'take_profit': 0.03,
                    'volume_threshold': 2.0,
                    'position_size': 0.08
                }
            },
            'DOGE_MTF': {
                'symbol': 'DOGE/USDT',
                'timeframe': 'MTF',
                'name': 'DOGE 多时间框架策略',
                'expected_return': 6.89,
                'win_rate': 63.3,
                'max_drawdown': 0.89,
                'params': {
                    'primary_tf': '4h',
                    'secondary_tf': '1h',
                    'entry_tf': '30m',
                    'signal_threshold': 0.7,
                    'volume_confirmation': 1.5,
                    'trend_confirmation': 3,
                    'momentum_threshold': 0.01,
                    'volatility_filter': 0.08,
                    'position_size': 0.15
                }
            }
        }
        
        # 实施状态
        self.implementation_status = {
            'phase': 'preparation',  # preparation, simulation, live_testing, production
            'active_strategies': [],
            'total_capital': 10000,
            'risk_per_trade': 0.01,
            'max_positions': 3
        }
    
    def display_implementation_menu(self):
        """显示实施菜单"""
        print("🚀 TradeFan 策略实施系统")
        print("=" * 60)
        print("📊 可用的优化策略:")
        
        for i, (key, strategy) in enumerate(self.optimized_strategies.items(), 1):
            print(f"   {i}. {strategy['name']}")
            print(f"      预期收益: {strategy['expected_return']:.2f}% | 胜率: {strategy['win_rate']:.1f}%")
            print(f"      最大回撤: {strategy['max_drawdown']:.2f}% | 时间框架: {strategy['timeframe']}")
            print()
        
        print("🎯 实施选项:")
        print("   A. 模拟交易测试 (推荐开始)")
        print("   B. 实时信号监控")
        print("   C. 策略性能监控")
        print("   D. 风险管理设置")
        print("   E. 全部策略状态")
        print("   Q. 退出")
        
        return input("\n请选择操作 (1-3/A-E/Q): ").strip().upper()
    
    def start_simulation_trading(self, strategy_key: str):
        """启动模拟交易"""
        strategy = self.optimized_strategies[strategy_key]
        
        print(f"\n🎯 启动模拟交易: {strategy['name']}")
        print("-" * 50)
        
        # 获取最新数据
        symbol = strategy['symbol']
        timeframe = strategy['timeframe'] if strategy['timeframe'] != 'MTF' else '30m'
        
        try:
            data = self.data_module.get_historical_data(symbol, timeframe)
            
            if data.empty:
                print(f"❌ 无法获取 {symbol} {timeframe} 数据")
                return
            
            print(f"✅ 数据获取成功: {len(data)} 条记录")
            print(f"   最新价格: ${data['close'].iloc[-1]:.6f}")
            print(f"   数据时间: {data['datetime'].iloc[-1]}")
            
            # 计算技术指标
            data_with_indicators = self.calculate_indicators(data, strategy['params'])
            
            # 生成当前信号
            current_signal = self.generate_signal(data_with_indicators, strategy)
            
            print(f"\n📊 当前市场分析:")
            self.display_market_analysis(data_with_indicators.iloc[-1], strategy)
            
            print(f"\n🎯 交易信号: {self.signal_to_text(current_signal)}")
            
            # 模拟交易记录
            self.simulate_trading_session(strategy_key, data_with_indicators)
            
        except Exception as e:
            print(f"❌ 模拟交易启动失败: {str(e)}")
    
    def calculate_indicators(self, data: pd.DataFrame, params: dict) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        try:
            # EMA指标
            if 'ema_fast' in params:
                df['ema_fast'] = df['close'].ewm(span=params['ema_fast'], adjust=False).mean()
                df['ema_medium'] = df['close'].ewm(span=params['ema_medium'], adjust=False).mean()
                df['ema_slow'] = df['close'].ewm(span=params['ema_slow'], adjust=False).mean()
            
            # 布林带
            if 'bb_std' in params:
                df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
                bb_std = df['close'].rolling(20, min_periods=1).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * params['bb_std'])
                df['bb_lower'] = df['bb_middle'] - (bb_std * params['bb_std'])
            
            # RSI
            if 'rsi_lower' in params:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14, min_periods=1).mean()
            
            # 成交量
            df['volume_ma'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
        except Exception as e:
            print(f"⚠️  指标计算警告: {str(e)}")
        
        return df
    
    def generate_signal(self, data: pd.DataFrame, strategy: dict) -> int:
        """生成交易信号"""
        if len(data) < 2:
            return 0
        
        current = data.iloc[-1]
        params = strategy['params']
        
        # 检查数据有效性
        if strategy['timeframe'] == 'MTF':
            # 多时间框架信号逻辑 (简化版)
            return self.generate_mtf_signal(current, params)
        else:
            # 单时间框架信号逻辑
            return self.generate_single_tf_signal(current, params)
    
    def generate_single_tf_signal(self, current: pd.Series, params: dict) -> int:
        """生成单时间框架信号"""
        try:
            # 多头条件
            long_conditions = [
                current.get('ema_fast', 0) > current.get('ema_medium', 0),
                current.get('ema_medium', 0) > current.get('ema_slow', 0),
                current.get('close', 0) > current.get('bb_middle', 0),
                params['rsi_lower'] < current.get('rsi', 50) < params['rsi_upper'],
                current.get('macd', 0) > current.get('macd_signal', 0),
                current.get('volume_ratio', 1) > params['volume_threshold']
            ]
            
            # 空头条件
            short_conditions = [
                current.get('ema_fast', 0) < current.get('ema_medium', 0),
                current.get('ema_medium', 0) < current.get('ema_slow', 0),
                current.get('close', 0) < current.get('bb_middle', 0),
                current.get('rsi', 50) < 30 or current.get('rsi', 50) > 70,
                current.get('macd', 0) < current.get('macd_signal', 0),
                current.get('volume_ratio', 1) > params['volume_threshold']
            ]
            
            long_score = sum(long_conditions)
            short_score = sum(short_conditions)
            
            if long_score >= 4:
                return 1  # 买入信号
            elif short_score >= 4:
                return -1  # 卖出信号
            else:
                return 0  # 无信号
                
        except Exception as e:
            print(f"⚠️  信号生成警告: {str(e)}")
            return 0
    
    def generate_mtf_signal(self, current: pd.Series, params: dict) -> int:
        """生成多时间框架信号 (简化版)"""
        # 这里是简化的MTF信号逻辑
        # 实际应用中需要获取多个时间框架的数据
        
        signal_strength = 0
        
        # 基于当前数据的简化判断
        if current.get('rsi', 50) > 30 and current.get('rsi', 50) < 70:
            signal_strength += 0.3
        
        if current.get('volume_ratio', 1) > params['volume_confirmation']:
            signal_strength += 0.4
        
        if current.get('macd', 0) > current.get('macd_signal', 0):
            signal_strength += 0.3
        
        if signal_strength > params['signal_threshold']:
            return 1
        elif signal_strength < -params['signal_threshold']:
            return -1
        else:
            return 0
    
    def display_market_analysis(self, current: pd.Series, strategy: dict):
        """显示市场分析"""
        print(f"   当前价格: ${current.get('close', 0):.6f}")
        
        if 'ema_fast' in current:
            print(f"   EMA趋势: 快线{current['ema_fast']:.6f} | 中线{current['ema_medium']:.6f} | 慢线{current['ema_slow']:.6f}")
        
        if 'rsi' in current:
            rsi_status = "超买" if current['rsi'] > 70 else "超卖" if current['rsi'] < 30 else "正常"
            print(f"   RSI: {current['rsi']:.1f} ({rsi_status})")
        
        if 'bb_middle' in current:
            bb_position = "上轨附近" if current['close'] > current['bb_upper'] * 0.98 else "下轨附近" if current['close'] < current['bb_lower'] * 1.02 else "中轨区间"
            print(f"   布林带: {bb_position}")
        
        if 'volume_ratio' in current:
            volume_status = "放量" if current['volume_ratio'] > 1.5 else "缩量" if current['volume_ratio'] < 0.8 else "正常"
            print(f"   成交量: {current['volume_ratio']:.2f}倍 ({volume_status})")
    
    def signal_to_text(self, signal: int) -> str:
        """信号转文字"""
        if signal == 1:
            return "🟢 买入信号"
        elif signal == -1:
            return "🔴 卖出信号"
        else:
            return "⚪ 观望"
    
    def simulate_trading_session(self, strategy_key: str, data: pd.DataFrame):
        """模拟交易会话"""
        strategy = self.optimized_strategies[strategy_key]
        
        print(f"\n🎮 模拟交易会话启动")
        print("-" * 40)
        
        # 模拟最近10个交易信号
        signals = []
        for i in range(max(0, len(data)-10), len(data)):
            if i < 50:  # 确保有足够的历史数据计算指标
                continue
                
            current_data = data.iloc[i]
            signal = self.generate_signal(data.iloc[:i+1], strategy)
            
            if signal != 0:
                signals.append({
                    'time': current_data['datetime'],
                    'price': current_data['close'],
                    'signal': signal,
                    'rsi': current_data.get('rsi', 0),
                    'volume_ratio': current_data.get('volume_ratio', 1)
                })
        
        if signals:
            print(f"📊 最近交易信号 (共{len(signals)}个):")
            for i, sig in enumerate(signals[-5:], 1):  # 显示最近5个信号
                signal_text = "买入" if sig['signal'] == 1 else "卖出"
                print(f"   {i}. {sig['time'].strftime('%m-%d %H:%M')} | {signal_text} | ${sig['price']:.6f} | RSI:{sig['rsi']:.1f}")
        else:
            print("📊 最近无交易信号")
        
        # 模拟交易建议
        current_signal = self.generate_signal(data, strategy)
        if current_signal != 0:
            self.generate_trading_recommendation(strategy, data.iloc[-1], current_signal)
    
    def generate_trading_recommendation(self, strategy: dict, current: pd.Series, signal: int):
        """生成交易建议"""
        print(f"\n💡 交易建议:")
        print("-" * 30)
        
        current_price = current['close']
        params = strategy['params']
        
        if signal == 1:  # 买入信号
            stop_loss_price = current_price * (1 - params.get('stop_loss', 0.02))
            take_profit_price = current_price * (1 + params.get('take_profit', 0.04))
            position_size = params.get('position_size', 0.1)
            
            print(f"🟢 建议买入 {strategy['symbol']}")
            print(f"   入场价格: ${current_price:.6f}")
            print(f"   止损价格: ${stop_loss_price:.6f} (-{params.get('stop_loss', 0.02)*100:.1f}%)")
            print(f"   止盈价格: ${take_profit_price:.6f} (+{params.get('take_profit', 0.04)*100:.1f}%)")
            print(f"   建议仓位: {position_size*100:.1f}%")
            print(f"   风险收益比: 1:{params.get('take_profit', 0.04)/params.get('stop_loss', 0.02):.1f}")
            
        elif signal == -1:  # 卖出信号
            print(f"🔴 建议卖出 {strategy['symbol']}")
            print(f"   如有持仓建议平仓")
            print(f"   或等待更好的买入机会")
    
    def start_real_time_monitoring(self):
        """启动实时监控"""
        print("\n📡 启动实时信号监控")
        print("=" * 50)
        print("⚠️  注意: 这是模拟监控，实际部署需要连接实时数据源")
        
        try:
            for i in range(5):  # 模拟5次监控循环
                print(f"\n🔄 监控周期 {i+1}/5 ({datetime.now().strftime('%H:%M:%S')})")
                
                for key, strategy in self.optimized_strategies.items():
                    symbol = strategy['symbol']
                    timeframe = strategy['timeframe'] if strategy['timeframe'] != 'MTF' else '30m'
                    
                    # 获取最新数据
                    data = self.data_module.get_historical_data(symbol, timeframe)
                    if not data.empty:
                        data_with_indicators = self.calculate_indicators(data, strategy['params'])
                        signal = self.generate_signal(data_with_indicators, strategy)
                        
                        status = self.signal_to_text(signal)
                        price = data['close'].iloc[-1]
                        
                        print(f"   {strategy['name']}: ${price:.6f} | {status}")
                
                if i < 4:  # 不在最后一次循环时等待
                    print("   等待下次监控...")
                    time.sleep(2)  # 实际应用中根据时间框架调整
                    
        except KeyboardInterrupt:
            print("\n⏹️  监控已停止")
        except Exception as e:
            print(f"\n❌ 监控出错: {str(e)}")
    
    def display_strategy_status(self):
        """显示策略状态"""
        print("\n📊 策略状态总览")
        print("=" * 60)
        
        for key, strategy in self.optimized_strategies.items():
            print(f"\n🎯 {strategy['name']}")
            print(f"   交易对: {strategy['symbol']}")
            print(f"   时间框架: {strategy['timeframe']}")
            print(f"   预期收益: {strategy['expected_return']:.2f}%")
            print(f"   预期胜率: {strategy['win_rate']:.1f}%")
            print(f"   最大回撤: {strategy['max_drawdown']:.2f}%")
            print(f"   建议仓位: {strategy['params'].get('position_size', 0.1)*100:.1f}%")
            
            # 获取当前信号状态
            try:
                symbol = strategy['symbol']
                timeframe = strategy['timeframe'] if strategy['timeframe'] != 'MTF' else '30m'
                data = self.data_module.get_historical_data(symbol, timeframe)
                
                if not data.empty:
                    data_with_indicators = self.calculate_indicators(data, strategy['params'])
                    signal = self.generate_signal(data_with_indicators, strategy)
                    print(f"   当前信号: {self.signal_to_text(signal)}")
                    print(f"   最新价格: ${data['close'].iloc[-1]:.6f}")
                else:
                    print(f"   状态: 数据获取失败")
                    
            except Exception as e:
                print(f"   状态: 检查失败 - {str(e)}")
    
    def run_implementation_system(self):
        """运行实施系统"""
        print("🚀 欢迎使用 TradeFan 策略实施系统")
        print("从优化策略到实际交易的完整解决方案")
        
        while True:
            try:
                choice = self.display_implementation_menu()
                
                if choice == 'Q':
                    print("\n👋 感谢使用 TradeFan 策略实施系统!")
                    break
                elif choice == '1':
                    self.start_simulation_trading('PEPE_4H')
                elif choice == '2':
                    self.start_simulation_trading('PEPE_30M')
                elif choice == '3':
                    self.start_simulation_trading('DOGE_MTF')
                elif choice == 'A':
                    print("\n选择要测试的策略:")
                    print("1. PEPE 4小时策略")
                    print("2. PEPE 30分钟策略") 
                    print("3. DOGE 多时间框架策略")
                    
                    strategy_choice = input("请选择 (1-3): ").strip()
                    if strategy_choice == '1':
                        self.start_simulation_trading('PEPE_4H')
                    elif strategy_choice == '2':
                        self.start_simulation_trading('PEPE_30M')
                    elif strategy_choice == '3':
                        self.start_simulation_trading('DOGE_MTF')
                elif choice == 'B':
                    self.start_real_time_monitoring()
                elif choice == 'C':
                    self.display_strategy_status()
                elif choice == 'D':
                    print("\n⚙️  风险管理设置")
                    print("   当前设置:")
                    print(f"   - 单笔风险: {self.implementation_status['risk_per_trade']*100:.1f}%")
                    print(f"   - 最大持仓: {self.implementation_status['max_positions']} 个")
                    print(f"   - 总资金: ${self.implementation_status['total_capital']:,}")
                elif choice == 'E':
                    self.display_strategy_status()
                else:
                    print("❌ 无效选择，请重新输入")
                
                input("\n按回车键继续...")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序已退出")
                break
            except Exception as e:
                print(f"\n❌ 系统错误: {str(e)}")
                input("按回车键继续...")


def main():
    """主函数"""
    implementation = StrategyImplementation()
    implementation.run_implementation_system()


if __name__ == "__main__":
    main()
