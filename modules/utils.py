"""
基础工具模块
提供配置加载、数据处理等通用功能
"""

import yaml
import os
from typing import Dict, Any
from dotenv import load_dotenv
import pandas as pd
import numpy as np

class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # 加载环境变量
            load_dotenv()
            
            # 从环境变量中获取API密钥
            if 'exchange' in config:
                config['exchange']['api_key'] = os.getenv('BINANCE_API_KEY', '')
                config['exchange']['secret'] = os.getenv('BINANCE_SECRET', '')
                
            return config
        except Exception as e:
            raise Exception(f"配置文件加载失败: {e}")
    
    def get(self, key: str, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_symbols(self) -> list:
        """获取启用的交易币种"""
        symbols = self.get('symbols', [])
        return [s for s in symbols if s.get('enabled', False)]

class DataProcessor:
    """数据处理工具类"""
    
    @staticmethod
    def calculate_returns(prices: pd.Series) -> pd.Series:
        """计算收益率"""
        return prices.pct_change().fillna(0)
    
    @staticmethod
    def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
        """计算累积收益率"""
        return (1 + returns).cumprod() - 1
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if returns.std() == 0:
            return 0
        excess_returns = returns.mean() * 252 - risk_free_rate
        return excess_returns / (returns.std() * np.sqrt(252))
    
    @staticmethod
    def calculate_max_drawdown(cumulative_returns: pd.Series) -> float:
        """计算最大回撤"""
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / (1 + peak)
        return drawdown.min()
    
    @staticmethod
    def calculate_win_rate(returns: pd.Series) -> float:
        """计算胜率"""
        if len(returns) == 0:
            return 0
        return (returns > 0).sum() / len(returns)

class OrderType:
    """订单类型枚举"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus:
    """订单状态枚举"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Position:
    """持仓信息类"""
    
    def __init__(self, symbol: str, size: float = 0, entry_price: float = 0):
        self.symbol = symbol
        self.size = size  # 正数为多头，负数为空头
        self.entry_price = entry_price
        self.unrealized_pnl = 0
        self.realized_pnl = 0
    
    def update_unrealized_pnl(self, current_price: float):
        """更新未实现盈亏"""
        if self.size != 0:
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
    
    def is_long(self) -> bool:
        """是否为多头持仓"""
        return self.size > 0
    
    def is_short(self) -> bool:
        """是否为空头持仓"""
        return self.size < 0
    
    def is_empty(self) -> bool:
        """是否为空仓"""
        return self.size == 0

class Order:
    """订单信息类"""
    
    def __init__(self, symbol: str, side: str, amount: float, price: float, 
                 order_type: str = "market", order_id: str = None):
        self.symbol = symbol
        self.side = side  # buy/sell
        self.amount = amount
        self.price = price
        self.order_type = order_type
        self.order_id = order_id or self._generate_order_id()
        self.status = OrderStatus.PENDING
        self.filled_amount = 0
        self.filled_price = 0
        self.timestamp = pd.Timestamp.now()
        self.commission = 0
    
    def _generate_order_id(self) -> str:
        """生成订单ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def fill(self, price: float, amount: float = None, commission: float = 0):
        """填充订单"""
        if amount is None:
            amount = self.amount
        
        self.filled_amount = amount
        self.filled_price = price
        self.commission = commission
        self.status = OrderStatus.FILLED
    
    def cancel(self):
        """取消订单"""
        self.status = OrderStatus.CANCELLED
