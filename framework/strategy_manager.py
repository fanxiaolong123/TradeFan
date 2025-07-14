"""
策略管理器
负责策略的创建、管理、组合和动态切换
支持策略池管理和性能监控
从core/移动到framework/，更新导入路径
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Type, Callable
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
from pathlib import Path

from .strategy_base import BaseStrategy, StrategyState
from .signal import Signal, SignalType
from core.config_manager import ConfigManager
from core.logger import LoggerManager


class StrategyManagerState(Enum):
    """策略管理器状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class StrategyFactory:
    """
    策略工厂
    负责策略类的注册和实例创建
    """
    
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
                       logger=None) -> BaseStrategy:
        """
        创建策略实例
        
        Args:
            strategy_type: 策略类型
            name: 策略名称
            config: 策略配置
            logger: 日志记录器
            
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
        
        return strategy_class(name, config, logger)
    
    def get_available_strategies(self) -> List[str]:
        """获取可用策略类型列表"""
        return list(self._strategy_classes.keys())
    
    def get_strategy_config_template(self, strategy_type: str) -> Dict[str, Any]:
        """获取策略配置模板"""
        return self._strategy_configs.get(strategy_type, {})


class StrategyManager:
    """
    策略管理器
    统一管理所有策略的生命周期、性能监控和配置
    """
    
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
        # 这里只注册基础的策略类型
        # 具体的策略实现将在strategies/目录中
        
        # 注册基础配置模板
        basic_config = {
            'parameters': {},
            'timeframes': ['1h'],
            'min_data_points': 50,
            'signal_cooldown': 300,
            'max_signals_per_hour': 10,
            'risk_settings': {
                'min_signal_strength': 0.2
            }
        }
        
        # 为不同策略类型设置默认配置
        strategy_types = ['trend_following', 'mean_reversion', 'breakout', 'momentum', 'scalping']
        for strategy_type in strategy_types:
            self.factory.register_config_template(strategy_type, basic_config.copy())
        
        self.logger.info(f"📚 注册基础策略配置模板: {strategy_types}")
    
    def register_strategy_class(self, strategy_type: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略类
        
        Args:
            strategy_type: 策略类型名称
            strategy_class: 策略类
        """
        self.factory.register_strategy(strategy_type, strategy_class)
        self.logger.info(f"📝 注册策略类: {strategy_type}")
    
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
        
        # 创建策略专用日志器
        strategy_logger = self.logger_manager.get_strategy_logger(name)
        
        strategy = self.factory.create_strategy(strategy_type, name, config, strategy_logger)
        
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
    
    def pause_strategy(self, name: str) -> bool:
        """暂停策略"""
        if name not in self.strategies:
            return False
        
        self.strategies[name].pause()
        self.logger.info(f"⏸️ 暂停策略: {name}")
        return True
    
    def resume_strategy(self, name: str) -> bool:
        """恢复策略"""
        if name not in self.strategies:
            return False
        
        self.strategies[name].resume()
        self.logger.info(f"▶️ 恢复策略: {name}")
        return True
    
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
    
    def get_manager_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        active_strategies = sum(1 for s in self.strategies.values() if s.state == StrategyState.ACTIVE)
        
        return {
            'state': self.state.value,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'total_strategies': len(self.strategies),
            'active_strategies': active_strategies,
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
                'max_signals_per_hour': strategy.max_signals_per_hour,
                'risk_settings': strategy.risk_settings
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
    
    def get_available_strategy_types(self) -> List[str]:
        """获取可用的策略类型"""
        return self.factory.get_available_strategies()
    
    def __str__(self):
        return f"StrategyManager(strategies={len(self.strategies)}, state={self.state.value})"
    
    def __repr__(self):
        return self.__str__()
