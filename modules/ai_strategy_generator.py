"""
AI策略生成器
使用AI自动生成和优化交易策略
"""

import json
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
from .log_module import LogModule
from .optimization_module import OptimizationManager
from .backtest_module import BacktestModule

class AIStrategyGenerator:
    """AI策略生成器"""
    
    def __init__(self, logger: LogModule = None):
        self.logger = logger or LogModule()
        
        # AI配置
        self.ai_config = {
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        # 策略模板
        self.strategy_templates = self._load_strategy_templates()
        
        # 生成的策略存储
        self.generated_strategies = {}
        
        self.logger.info("AI策略生成器初始化完成")
    
    def _load_strategy_templates(self) -> Dict[str, str]:
        """加载策略模板"""
        return {
            'trend_following': '''
class {strategy_name}(BaseStrategy):
    """AI生成的趋势跟踪策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        # 策略参数
        {parameters}
        
        if self.logger:
            self.logger.info(f"初始化{strategy_name}: {param_description}")
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术指标"""
        indicators = {{}}
        
        try:
            {indicator_calculations}
        except Exception as e:
            if self.logger:
                self.logger.error(f"指标计算失败: {{e}}")
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < {min_data_length}:
            return signals
        
        indicators = self.calculate_indicators(data)
        
        try:
            {signal_logic}
        except Exception as e:
            if self.logger:
                self.logger.error(f"信号生成失败: {{e}}")
        
        return signals
            ''',
            
            'mean_reversion': '''
class {strategy_name}(BaseStrategy):
    """AI生成的均值回归策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        # 策略参数
        {parameters}
        
        if self.logger:
            self.logger.info(f"初始化{strategy_name}: {param_description}")
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算技术指标"""
        indicators = {{}}
        
        try:
            {indicator_calculations}
        except Exception as e:
            if self.logger:
                self.logger.error(f"指标计算失败: {{e}}")
        
        return indicators
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if len(data) < {min_data_length}:
            return signals
        
        indicators = self.calculate_indicators(data)
        
        try:
            {signal_logic}
        except Exception as e:
            if self.logger:
                self.logger.error(f"信号生成失败: {{e}}")
        
        return signals
            '''
        }
    
    def generate_strategy_idea(self, market_condition: str = "trending", 
                             performance_target: Dict = None) -> Dict[str, Any]:
        """生成策略想法"""
        if performance_target is None:
            performance_target = {
                'target_return': 0.15,  # 15%年化收益
                'max_drawdown': 0.1,    # 10%最大回撤
                'sharpe_ratio': 1.5     # 夏普比率1.5
            }
        
        # 基于市场条件生成策略想法
        strategy_ideas = {
            'trending': {
                'type': 'trend_following',
                'description': '趋势跟踪策略，适用于趋势明显的市场',
                'indicators': ['移动平均线', 'MACD', 'ADX', '布林带'],
                'entry_conditions': ['价格突破移动平均线', 'MACD金叉', 'ADX上升'],
                'exit_conditions': ['价格跌破移动平均线', 'MACD死叉', '止损止盈']
            },
            'sideways': {
                'type': 'mean_reversion',
                'description': '均值回归策略，适用于震荡市场',
                'indicators': ['RSI', '布林带', '随机指标', '威廉指标'],
                'entry_conditions': ['RSI超卖反弹', '价格触及布林带下轨'],
                'exit_conditions': ['RSI超买', '价格触及布林带上轨']
            },
            'volatile': {
                'type': 'breakout',
                'description': '突破策略，适用于高波动市场',
                'indicators': ['ATR', '唐奇安通道', '成交量', '价格区间'],
                'entry_conditions': ['价格突破通道', '成交量放大确认'],
                'exit_conditions': ['价格回落到通道内', '止损止盈']
            }
        }
        
        idea = strategy_ideas.get(market_condition, strategy_ideas['trending'])
        idea['performance_target'] = performance_target
        idea['timestamp'] = datetime.now().isoformat()
        
    
    def generate_strategy_code(self, strategy_idea: Dict[str, Any]) -> str:
        """根据策略想法生成代码"""
        strategy_type = strategy_idea.get('type', 'trend_following')
        strategy_name = f"AI_{strategy_type.title()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 生成参数
        parameters = self._generate_parameters(strategy_idea)
        param_description = self._generate_param_description(parameters)
        
        # 生成指标计算代码
        indicator_calculations = self._generate_indicator_code(strategy_idea['indicators'])
        
        # 生成信号逻辑代码
        signal_logic = self._generate_signal_logic(strategy_idea)
        
        # 选择模板
        template = self.strategy_templates.get(strategy_type, self.strategy_templates['trend_following'])
        
        # 填充模板
        strategy_code = template.format(
            strategy_name=strategy_name,
            parameters=parameters,
            param_description=param_description,
            indicator_calculations=indicator_calculations,
            signal_logic=signal_logic,
            min_data_length=50
        )
        
        self.logger.info(f"生成策略代码: {strategy_name}")
        return strategy_code
    
    def _generate_parameters(self, strategy_idea: Dict[str, Any]) -> str:
        """生成策略参数"""
        strategy_type = strategy_idea.get('type', 'trend_following')
        
        if strategy_type == 'trend_following':
            return '''
        self.fast_ma = params.get('fast_ma', 12)
        self.slow_ma = params.get('slow_ma', 26)
        self.signal_ma = params.get('signal_ma', 9)
        self.atr_period = params.get('atr_period', 14)
        self.atr_multiplier = params.get('atr_multiplier', 2.0)
            '''
        elif strategy_type == 'mean_reversion':
            return '''
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.rsi_overbought = params.get('rsi_overbought', 70)
        self.bb_period = params.get('bb_period', 20)
        self.bb_std = params.get('bb_std', 2.0)
            '''
        else:
            return '''
        self.lookback_period = params.get('lookback_period', 20)
        self.breakout_threshold = params.get('breakout_threshold', 0.02)
        self.volume_threshold = params.get('volume_threshold', 1.5)
            '''
    
    def _generate_param_description(self, parameters: str) -> str:
        """生成参数描述"""
        # 简化的参数描述生成
        return "AI生成的策略参数"
    
    def _generate_indicator_code(self, indicators: List[str]) -> str:
        """生成指标计算代码"""
        code_parts = []
        
        for indicator in indicators:
            if '移动平均线' in indicator or 'MA' in indicator:
                code_parts.append('''
            # 移动平均线
            indicators['fast_ma'] = talib.SMA(data['close'].values, timeperiod=self.fast_ma)
            indicators['slow_ma'] = talib.SMA(data['close'].values, timeperiod=self.slow_ma)
                ''')
            
            elif 'MACD' in indicator:
                code_parts.append('''
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(data['close'].values)
            indicators['macd'] = pd.Series(macd, index=data.index)
            indicators['macd_signal'] = pd.Series(macd_signal, index=data.index)
            indicators['macd_hist'] = pd.Series(macd_hist, index=data.index)
                ''')
            
            elif 'RSI' in indicator:
                code_parts.append('''
            # RSI
            rsi = talib.RSI(data['close'].values, timeperiod=self.rsi_period)
            indicators['rsi'] = pd.Series(rsi, index=data.index)
                ''')
            
            elif '布林带' in indicator or 'Bollinger' in indicator:
                code_parts.append('''
            # 布林带
            bb_upper, bb_middle, bb_lower = talib.BBANDS(data['close'].values, timeperiod=self.bb_period)
            indicators['bb_upper'] = pd.Series(bb_upper, index=data.index)
            indicators['bb_middle'] = pd.Series(bb_middle, index=data.index)
            indicators['bb_lower'] = pd.Series(bb_lower, index=data.index)
                ''')
            
            elif 'ATR' in indicator:
                code_parts.append('''
            # ATR
            atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=self.atr_period)
            indicators['atr'] = pd.Series(atr, index=data.index)
                ''')
        
        return '\n'.join(code_parts)
    
    def _generate_signal_logic(self, strategy_idea: Dict[str, Any]) -> str:
        """生成信号逻辑代码"""
        strategy_type = strategy_idea.get('type', 'trend_following')
        
        if strategy_type == 'trend_following':
            return '''
            # 趋势跟踪信号
            fast_ma = indicators.get('fast_ma')
            slow_ma = indicators.get('slow_ma')
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            
            if fast_ma is not None and slow_ma is not None:
                # 均线交叉信号
                buy_signal = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
                sell_signal = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
                
                signals[buy_signal] = 1
                signals[sell_signal] = -1
            
            if macd is not None and macd_signal is not None:
                # MACD确认信号
                macd_buy = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
                macd_sell = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))
                
                # 与均线信号结合
                signals[macd_buy & (signals == 0)] = 1
                signals[macd_sell & (signals == 0)] = -1
            '''
        
        elif strategy_type == 'mean_reversion':
            return '''
            # 均值回归信号
            rsi = indicators.get('rsi')
            bb_upper = indicators.get('bb_upper')
            bb_lower = indicators.get('bb_lower')
            
            if rsi is not None:
                # RSI超买超卖信号
                buy_signal = (rsi < self.rsi_oversold) & (rsi.shift(1) >= self.rsi_oversold)
                sell_signal = (rsi > self.rsi_overbought) & (rsi.shift(1) <= self.rsi_overbought)
                
                signals[buy_signal] = 1
                signals[sell_signal] = -1
            
            if bb_upper is not None and bb_lower is not None:
                # 布林带反转信号
                bb_buy = (data['close'] < bb_lower) & (data['close'].shift(1) >= bb_lower)
                bb_sell = (data['close'] > bb_upper) & (data['close'].shift(1) <= bb_upper)
                
                # 与RSI信号结合
                signals[bb_buy & (signals == 0)] = 1
                signals[bb_sell & (signals == 0)] = -1
            '''
        
        else:
            return '''
            # 突破策略信号
            high_max = data['high'].rolling(window=self.lookback_period).max()
            low_min = data['low'].rolling(window=self.lookback_period).min()
            
            # 突破信号
            buy_signal = data['close'] > high_max.shift(1) * (1 + self.breakout_threshold)
            sell_signal = data['close'] < low_min.shift(1) * (1 - self.breakout_threshold)
            
            signals[buy_signal] = 1
            signals[sell_signal] = -1
            '''
    
    def save_strategy(self, strategy_code: str, strategy_name: str) -> str:
        """保存策略代码到文件"""
        strategies_dir = "strategies/ai_generated"
        os.makedirs(strategies_dir, exist_ok=True)
        
        file_path = f"{strategies_dir}/{strategy_name}.py"
        
        # 添加必要的导入
        full_code = '''"""
AI生成的交易策略
自动生成时间: {timestamp}
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict
from modules.strategy_module import BaseStrategy

{strategy_code}
        '''.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            strategy_code=strategy_code
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_code)
        
        self.logger.info(f"策略代码已保存: {file_path}")
        return file_path
