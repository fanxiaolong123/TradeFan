"""
策略管理器
负责策略的创建、管理、组合和动态切换
支持策略池管理和性能监控
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Type, Callable
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
from pathlib import Path

from .strategy_base import BaseStrategy, Signal, SignalType, StrategyState
from .config_manager import ConfigManager
from .logger import LoggerManager


class StrategyManagerState(Enum):
    """策略管理器状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class StrategyFactory:
    """策略工厂"""
    
    def __init__(self):
        self._strategy_classes: Dict[str, Type[BaseStrategy]] = {}
        self._strategy_configs: Dict[str, Dict] = {}
        
    def register_strategy(self, strategy_type: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略类
        
        Args:
            strategy_type: 策略类型名称
            strategy_class: 策略类
        """
        self._strategy_classes[strategy_type] = strategy_class
        
    def register_config_template(self, strategy_type: str, config_template: Dict[str, Any]):
        """
        注册策略配置模板
        
        Args:
            strategy_type: 策略类型
            config_template: 配置模板
        """
        self._strategy_configs[strategy_type] = config_template
    
    def create_strategy(self, strategy_type: str, name: str, config: Dict[str, Any],
                       logger_manager: LoggerManager = None) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            strategy_type: 策略类型
            name: 策略名称
            config: 策略配置
            logger_manager: 日志管理器
            
        Returns:
            策略实例
        """
        if strategy_type not in self._strategy_classes:
            raise ValueError(f"未知策略类型: {strategy_type}")
        
        strategy_class = self._strategy_classes[strategy_type]
        
        # 合并默认配置
        if strategy_type in self._strategy_configs:
            default_config = self._strategy_configs[strategy_type].copy()
            default_config.update(config)
            config = default_config
        
        return strategy_class(name, config, logger_manager)
    
    def get_available_strategies(self) -> List[str]:
        """获取可用策略类型列表"""
        return list(self._strategy_classes.keys())
    
    def get_strategy_config_template(self, strategy_type: str) -> Dict[str, Any]:
        """获取策略配置模板"""
        return self._strategy_configs.get(strategy_type, {})


class StrategyPortfolio:
    """策略组合"""
    
    def __init__(self, name: str, strategies: List[BaseStrategy], 
                 weights: Optional[List[float]] = None):
        """
        初始化策略组合
        
        Args:
            name: 组合名称
            strategies: 策略列表
            weights: 策略权重列表
        """
        self.name = name
        self.strategies = strategies
        self.weights = weights or [1.0 / len(strategies)] * len(strategies)
        
        if len(self.weights) != len(self.strategies):
            raise ValueError("策略数量与权重数量不匹配")
        
        if abs(sum(self.weights) - 1.0) > 0.01:
            raise ValueError("权重总和必须为1.0")
        
        self.created_time = datetime.now()
        self.last_rebalance_time = None
        
    async def generate_combined_signal(self, market_data: Dict[str, pd.DataFrame], 
                                     symbol: str) -> Signal:
        """
        生成组合信号
        
        Args:
            market_data: 市场数据
            symbol: 交易对
            
        Returns:
            组合信号
        """
        signals = []
        
        # 收集各策略信号
        for strategy in self.strategies:
            if strategy.state == StrategyState.ACTIVE:
                try:
                    strategy_signals = await strategy.process_data({symbol: market_data[symbol]})
                    if symbol in strategy_signals:
                        signals.append(strategy_signals[symbol])
                except Exception as e:
                    continue
        
        if not signals:
            return Signal(SignalType.HOLD, 0, market_data[symbol]['close'].iloc[-1], 
                         "无有效策略信号", {'symbol': symbol})
        
        # 计算加权信号
        weighted_signal = 0
        weighted_strength = 0
        total_weight = 0
        reasons = []
        
        for i, signal in enumerate(signals):
            if i < len(self.weights):
                weight = self.weights[i]
                weighted_signal += signal.signal_type.value * weight
                weighted_strength += signal.strength * weight
                total_weight += weight
                reasons.append(f"{self.strategies[i].name}:{signal.reason}")
        
        if total_weight == 0:
            return Signal(SignalType.HOLD, 0, market_data[symbol]['close'].iloc[-1], 
                         "权重为零", {'symbol': symbol})
        
        # 标准化
        final_signal_value = weighted_signal / total_weight
        final_strength = weighted_strength / total_weight
        
        # 确定最终信号类型
        if final_signal_value > 0.5:
            signal_type = SignalType.STRONG_BUY if final_strength > 0.7 else SignalType.BUY
        elif final_signal_value < -0.5:
            signal_type = SignalType.STRONG_SELL if final_strength > 0.7 else SignalType.SELL
        else:
            signal_type = SignalType.HOLD
        
        return Signal(
            signal_type,
            final_strength,
            market_data[symbol]['close'].iloc[-1],
            f"组合信号: {'; '.join(reasons)}",
            {'symbol': symbol, 'portfolio': self.name, 'component_signals': len(signals)}
        )
    
    def rebalance(self, new_weights: List[float]):
        """重新平衡策略权重"""
        if len(new_weights) != len(self.strategies):
            raise ValueError("权重数量与策略数量不匹配")
        
        if abs(sum(new_weights) - 1.0) > 0.01:
            raise ValueError("权重总和必须为1.0")
        
        old_weights = self.weights.copy()
        self.weights = new_weights
        self.last_rebalance_time = datetime.now()
        
        return {
            'old_weights': old_weights,
            'new_weights': new_weights,
            'rebalance_time': self.last_rebalance_time.isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取组合状态"""
        return {
            'name': self.name,
            'strategies': [s.name for s in self.strategies],
            'weights': self.weights,
            'created_time': self.created_time.isoformat(),
            'last_rebalance_time': self.last_rebalance_time.isoformat() if self.last_rebalance_time else None,
            'active_strategies': sum(1 for s in self.strategies if s.state == StrategyState.ACTIVE)
        }


class StrategyManager:
    """策略管理器"""
    
    def __init__(self, config_manager: ConfigManager, logger_manager: LoggerManager):
        """
        初始化策略管理器
        
        Args:
            config_manager: 配置管理器
            logger_manager: 日志管理器
        """
        self.config_manager = config_manager
        self.logger_manager = logger_manager
        self.logger = logger_manager.create_logger("StrategyManager")
        
        # 策略工厂
        self.factory = StrategyFactory()
        
        # 策略实例管理
        self.strategies: Dict[str, BaseStrategy] = {}
        self.portfolios: Dict[str, StrategyPortfolio] = {}
        
        # 管理器状态
        self.state = StrategyManagerState.STOPPED
        self.start_time = None
        self.last_update_time = None
        
        # 性能统计
        self.total_signals_generated = 0
        self.strategy_performance: Dict[str, Dict] = {}
        
        # 初始化内置策略
        self._register_builtin_strategies()
        
        self.logger.info("🎯 策略管理器初始化完成")
    
    def _register_builtin_strategies(self):
        """注册内置策略"""
        from .strategy_base import TrendFollowingStrategy
        
        # 注册趋势跟踪策略
        self.factory.register_strategy("trend_following", TrendFollowingStrategy)
        self.factory.register_config_template("trend_following", {
            'parameters': {
                'fast_ema': 8,
                'slow_ema': 21,
                'rsi_threshold': 50
            },
            'timeframes': ['1h'],
            'min_data_points': 50,
            'signal_cooldown': 300,
            'max_signals_per_hour': 10
        })
        
        # 可以继续注册更多策略...
        
        self.logger.info(f"📚 注册内置策略: {self.factory.get_available_strategies()}")
    
    def create_strategy(self, strategy_type: str, name: str, 
                       config: Dict[str, Any] = None) -> BaseStrategy:
        """
        创建策略
        
        Args:
            strategy_type: 策略类型
            name: 策略名称
            config: 策略配置
            
        Returns:
            创建的策略实例
        """
        if name in self.strategies:
            raise ValueError(f"策略名称已存在: {name}")
        
        config = config or {}
        strategy = self.factory.create_strategy(strategy_type, name, config, self.logger_manager)
        
        self.strategies[name] = strategy
        self.strategy_performance[name] = {
            'created_time': datetime.now().isoformat(),
            'total_signals': 0,
            'last_signal_time': None,
            'avg_strength': 0.0
        }
        
        self.logger.info(f"✅ 创建策略: {name} ({strategy_type})")
        return strategy
    
    def remove_strategy(self, name: str) -> bool:
        """
        移除策略
        
        Args:
            name: 策略名称
            
        Returns:
            是否成功移除
        """
        if name not in self.strategies:
            return False
        
        strategy = self.strategies[name]
        strategy.deactivate()
        
        del self.strategies[name]
        del self.strategy_performance[name]
        
        self.logger.info(f"🗑️ 移除策略: {name}")
        return True
    
    def activate_strategy(self, name: str) -> bool:
        """激活策略"""
        if name not in self.strategies:
            return False
        
        self.strategies[name].activate()
        self.logger.info(f"▶️ 激活策略: {name}")
        return True
    
    def deactivate_strategy(self, name: str) -> bool:
        """停用策略"""
        if name not in self.strategies:
            return False
        
        self.strategies[name].deactivate()
        self.logger.info(f"⏹️ 停用策略: {name}")
        return True
    
    def create_portfolio(self, name: str, strategy_names: List[str], 
                        weights: Optional[List[float]] = None) -> StrategyPortfolio:
        """
        创建策略组合
        
        Args:
            name: 组合名称
            strategy_names: 策略名称列表
            weights: 权重列表
            
        Returns:
            策略组合
        """
        if name in self.portfolios:
            raise ValueError(f"组合名称已存在: {name}")
        
        strategies = []
        for strategy_name in strategy_names:
            if strategy_name not in self.strategies:
                raise ValueError(f"策略不存在: {strategy_name}")
            strategies.append(self.strategies[strategy_name])
        
        portfolio = StrategyPortfolio(name, strategies, weights)
        self.portfolios[name] = portfolio
        
        self.logger.info(f"📊 创建策略组合: {name} (策略: {strategy_names})")
        return portfolio
    
    async def process_market_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Signal]]:
        """
        处理市场数据，生成所有策略信号
        
        Args:
            market_data: 市场数据 {symbol: DataFrame}
            
        Returns:
            信号字典 {strategy_name: {symbol: Signal}}
        """
        all_signals = {}
        
        # 处理单个策略
        for strategy_name, strategy in self.strategies.items():
            if strategy.state == StrategyState.ACTIVE:
                try:
                    signals = await strategy.process_data(market_data)
                    if signals:
                        all_signals[strategy_name] = signals
                        
                        # 更新性能统计
                        self.strategy_performance[strategy_name]['total_signals'] += len(signals)
                        self.strategy_performance[strategy_name]['last_signal_time'] = datetime.now().isoformat()
                        
                        total_strength = sum(s.strength for s in signals.values())
                        self.strategy_performance[strategy_name]['avg_strength'] = total_strength / len(signals)
                        
                except Exception as e:
                    self.logger.error(f"❌ 策略 {strategy_name} 处理失败: {e}")
                    continue
        
        # 处理策略组合
        for portfolio_name, portfolio in self.portfolios.items():
            try:
                portfolio_signals = {}
                for symbol in market_data.keys():
                    signal = await portfolio.generate_combined_signal(market_data, symbol)
                    if signal.signal_type != SignalType.HOLD:
                        portfolio_signals[symbol] = signal
                
                if portfolio_signals:
                    all_signals[f"portfolio_{portfolio_name}"] = portfolio_signals
                    
            except Exception as e:
                self.logger.error(f"❌ 组合 {portfolio_name} 处理失败: {e}")
                continue
        
        self.total_signals_generated += sum(len(signals) for signals in all_signals.values())
        self.last_update_time = datetime.now()
        
        return all_signals
    
    def get_strategy_status(self, name: str = None) -> Dict[str, Any]:
        """获取策略状态"""
        if name:
            if name in self.strategies:
                return self.strategies[name].get_status()
            else:
                return {}
        else:
            return {strategy_name: strategy.get_status() 
                   for strategy_name, strategy in self.strategies.items()}
    
    def get_portfolio_status(self, name: str = None) -> Dict[str, Any]:
        """获取组合状态"""
        if name:
            if name in self.portfolios:
                return self.portfolios[name].get_status()
            else:
                return {}
        else:
            return {portfolio_name: portfolio.get_status() 
                   for portfolio_name, portfolio in self.portfolios.items()}
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        active_strategies = sum(1 for s in self.strategies.values() if s.state == StrategyState.ACTIVE)
        
        return {
            'state': self.state.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'total_strategies': len(self.strategies),
            'active_strategies': active_strategies,
            'total_portfolios': len(self.portfolios),
            'total_signals_generated': self.total_signals_generated,
            'available_strategy_types': self.factory.get_available_strategies(),
            'strategy_performance': self.strategy_performance
        }
    
    def export_strategy_config(self, name: str) -> Dict[str, Any]:
        """导出策略配置"""
        if name not in self.strategies:
            return {}
        
        strategy = self.strategies[name]
        return {
            'name': name,
            'type': strategy.__class__.__name__,
            'config': {
                'parameters': strategy.parameters,
                'timeframes': strategy.timeframes,
                'symbols': strategy.symbols,
                'min_data_points': strategy.min_data_points,
                'signal_cooldown': strategy.signal_cooldown,
                'max_signals_per_hour': strategy.max_signals_per_hour
            },
            'status': strategy.get_status()
        }
    
    def import_strategy_config(self, config: Dict[str, Any]) -> BaseStrategy:
        """导入策略配置"""
        strategy_type = config.get('type', 'trend_following')
        name = config['name']
        strategy_config = config.get('config', {})
        
        return self.create_strategy(strategy_type, name, strategy_config)
    
    def save_strategies_to_file(self, file_path: str):
        """保存策略配置到文件"""
        configs = []
        for name in self.strategies.keys():
            configs.append(self.export_strategy_config(name))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 策略配置已保存到: {file_path}")
    
    def load_strategies_from_file(self, file_path: str):
        """从文件加载策略配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                configs = json.load(f)
            
            loaded_count = 0
            for config in configs:
                try:
                    self.import_strategy_config(config)
                    loaded_count += 1
                except Exception as e:
                    self.logger.error(f"❌ 加载策略失败 {config.get('name', 'Unknown')}: {e}")
            
            self.logger.info(f"📂 从文件加载策略: {loaded_count}/{len(configs)}")
            
        except Exception as e:
            self.logger.error(f"❌ 加载策略文件失败: {e}")
    
    def start(self):
        """启动策略管理器"""
        self.state = StrategyManagerState.RUNNING
        self.start_time = datetime.now()
        self.logger.info("🚀 策略管理器启动")
    
    def stop(self):
        """停止策略管理器"""
        # 停用所有策略
        for strategy in self.strategies.values():
            strategy.deactivate()
        
        self.state = StrategyManagerState.STOPPED
        self.logger.info("⏹️ 策略管理器停止")
    
    def __str__(self):
        return f"StrategyManager(strategies={len(self.strategies)}, portfolios={len(self.portfolios)})"
    
    def __repr__(self):
        return self.__str__()
