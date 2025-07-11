"""
策略基类
定义所有策略必须实现的接口
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

class BaseStrategy(ABC):
    """策略抽象基类"""
    
    def __init__(self, **params):
        """
        初始化策略
        
        Args:
            **params: 策略参数
        """
        self.params = params
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.description = ""
        self.author = "TradeFan"
        
        # 验证参数
        self._validate_params()
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            data: OHLCV数据，包含columns: ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            添加了技术指标的DataFrame
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含技术指标的OHLCV数据
            
        Returns:
            添加了信号列的DataFrame，包含:
            - signal: 1(买入), -1(卖出), 0(无信号)
            - position: 当前持仓状态
        """
        pass
    
    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """
        获取默认参数
        
        Returns:
            默认参数字典
        """
        pass
    
    def _validate_params(self):
        """验证策略参数"""
        default_params = self.get_default_params()
        
        # 检查必需参数
        for key, default_value in default_params.items():
            if key not in self.params:
                self.params[key] = default_value
        
        # 子类可以重写此方法进行更严格的参数验证
        self._custom_validate_params()
    
    def _custom_validate_params(self):
        """自定义参数验证，子类可重写"""
        pass
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'params': self.params.copy()
        }
    
    def get_param_ranges(self) -> Dict[str, Tuple]:
        """
        获取参数优化范围
        用于参数搜索
        
        Returns:
            参数范围字典，格式: {'param_name': (min_val, max_val, step)}
        """
        return {}
    
    def calculate_position_size(self, signal: int, current_price: float, 
                              available_capital: float, risk_params: Dict) -> float:
        """
        计算仓位大小
        
        Args:
            signal: 交易信号
            current_price: 当前价格
            available_capital: 可用资金
            risk_params: 风险参数
            
        Returns:
            仓位大小
        """
        if signal == 0:
            return 0
        
        # 默认使用固定比例
        position_ratio = risk_params.get('position_ratio', 0.1)
        max_position_value = available_capital * position_ratio
        
        return max_position_value / current_price if current_price > 0 else 0
    
    def should_exit_position(self, current_price: float, entry_price: float, 
                           position_side: int, risk_params: Dict) -> Tuple[bool, str]:
        """
        判断是否应该退出仓位
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            position_side: 仓位方向 (1: 多头, -1: 空头)
            risk_params: 风险参数
            
        Returns:
            (是否退出, 退出原因)
        """
        if entry_price <= 0:
            return False, ""
        
        # 计算盈亏比例
        if position_side == 1:  # 多头
            pnl_ratio = (current_price - entry_price) / entry_price
        else:  # 空头
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 止损检查
        stop_loss = risk_params.get('stop_loss', 0.02)
        if pnl_ratio <= -stop_loss:
            return True, f"止损触发 (亏损{pnl_ratio:.2%})"
        
        # 止盈检查
        take_profit = risk_params.get('take_profit', 0.04)
        if pnl_ratio >= take_profit:
            return True, f"止盈触发 (盈利{pnl_ratio:.2%})"
        
        return False, ""
    
    def get_signal_strength(self, data: pd.DataFrame, index: int) -> float:
        """
        获取信号强度 (0-1)
        用于仓位管理和信号过滤
        
        Args:
            data: 数据
            index: 当前索引
            
        Returns:
            信号强度 (0-1)
        """
        return 1.0  # 默认返回最大强度
    
    def __str__(self):
        return f"{self.name}({self.params})"
    
    def __repr__(self):
        return self.__str__()
