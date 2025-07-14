"""
交易信号系统
定义标准化的交易信号格式和处理逻辑
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional


class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1          # 买入信号
    SELL = -1        # 卖出信号  
    HOLD = 0         # 持有信号
    STRONG_BUY = 2   # 强买入信号
    STRONG_SELL = -2 # 强卖出信号


class Signal:
    """
    交易信号类
    标准化的信号格式，包含信号类型、强度、价格、原因等信息
    """
    
    def __init__(self, signal_type: SignalType, strength: float, 
                 price: float, reason: str, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化交易信号
        
        Args:
            signal_type: 信号类型 (BUY/SELL/HOLD等)
            strength: 信号强度 (0-1之间)
            price: 触发价格
            reason: 信号产生原因
            metadata: 额外的元数据信息
        """
        self.signal_type = signal_type
        self.strength = max(0, min(1, strength))  # 限制在0-1之间
        self.price = price
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.symbol = self.metadata.get('symbol', '')
        
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            包含信号所有信息的字典
        """
        return {
            'signal': self.signal_type.value,
            'signal_name': self.signal_type.name,
            'strength': self.strength,
            'price': self.price,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'metadata': self.metadata
        }
    
    def is_entry_signal(self) -> bool:
        """
        判断是否为入场信号
        
        Returns:
            True如果是买入或卖出信号
        """
        return self.signal_type in [SignalType.BUY, SignalType.SELL, 
                                   SignalType.STRONG_BUY, SignalType.STRONG_SELL]
    
    def is_strong_signal(self) -> bool:
        """
        判断是否为强信号
        
        Returns:
            True如果是强买入或强卖出信号
        """
        return self.signal_type in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]
    
    def is_buy_signal(self) -> bool:
        """判断是否为买入信号"""
        return self.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]
    
    def is_sell_signal(self) -> bool:
        """判断是否为卖出信号"""
        return self.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]
    
    def get_direction(self) -> int:
        """
        获取信号方向
        
        Returns:
            1: 多头, -1: 空头, 0: 中性
        """
        if self.is_buy_signal():
            return 1
        elif self.is_sell_signal():
            return -1
        else:
            return 0
    
    def get_weighted_strength(self) -> float:
        """
        获取加权强度 (考虑信号类型)
        
        Returns:
            加权后的信号强度
        """
        base_strength = self.strength
        
        # 强信号获得额外权重
        if self.is_strong_signal():
            base_strength *= 1.2
        
        return min(1.0, base_strength)
    
    def __str__(self):
        """字符串表示"""
        return f"Signal({self.signal_type.name}, {self.strength:.2f}, {self.reason})"
    
    def __repr__(self):
        """详细字符串表示"""
        return (f"Signal(type={self.signal_type.name}, strength={self.strength:.2f}, "
                f"price={self.price}, symbol={self.symbol}, reason='{self.reason}')")


class SignalAggregator:
    """
    信号聚合器
    用于合并多个策略的信号
    """
    
    @staticmethod
    def weighted_average(signals: list[Signal], weights: list[float]) -> Signal:
        """
        加权平均合并信号
        
        Args:
            signals: 信号列表
            weights: 权重列表
            
        Returns:
            合并后的信号
        """
        if not signals:
            raise ValueError("信号列表不能为空")
        
        if len(signals) != len(weights):
            raise ValueError("信号数量与权重数量不匹配")
        
        if abs(sum(weights) - 1.0) > 0.01:
            raise ValueError("权重总和必须为1.0")
        
        # 计算加权信号值和强度
        weighted_signal = 0
        weighted_strength = 0
        total_weight = 0
        reasons = []
        
        for signal, weight in zip(signals, weights):
            weighted_signal += signal.signal_type.value * weight
            weighted_strength += signal.strength * weight
            total_weight += weight
            reasons.append(f"{signal.reason}(权重{weight:.1f})")
        
        # 确定最终信号类型
        if weighted_signal > 0.5:
            final_signal_type = SignalType.STRONG_BUY if weighted_strength > 0.7 else SignalType.BUY
        elif weighted_signal < -0.5:
            final_signal_type = SignalType.STRONG_SELL if weighted_strength > 0.7 else SignalType.SELL
        else:
            final_signal_type = SignalType.HOLD
        
        # 使用第一个信号的价格和符号
        first_signal = signals[0]
        
        return Signal(
            signal_type=final_signal_type,
            strength=weighted_strength,
            price=first_signal.price,
            reason=f"加权合并: {'; '.join(reasons)}",
            metadata={
                'symbol': first_signal.symbol,
                'aggregation_method': 'weighted_average',
                'component_signals': len(signals),
                'weights': weights
            }
        )
    
    @staticmethod
    def majority_vote(signals: list[Signal]) -> Signal:
        """
        多数投票合并信号
        
        Args:
            signals: 信号列表
            
        Returns:
            合并后的信号
        """
        if not signals:
            raise ValueError("信号列表不能为空")
        
        # 统计各类型信号数量
        signal_counts = {}
        total_strength = 0
        
        for signal in signals:
            signal_type = signal.signal_type
            if signal_type not in signal_counts:
                signal_counts[signal_type] = []
            signal_counts[signal_type].append(signal)
            total_strength += signal.strength
        
        # 找出最多的信号类型
        majority_type = max(signal_counts.keys(), key=lambda x: len(signal_counts[x]))
        majority_signals = signal_counts[majority_type]
        
        # 计算平均强度
        avg_strength = total_strength / len(signals)
        
        # 合并原因
        reasons = [s.reason for s in majority_signals]
        
        return Signal(
            signal_type=majority_type,
            strength=avg_strength,
            price=signals[0].price,
            reason=f"多数投票({len(majority_signals)}/{len(signals)}): {'; '.join(reasons[:3])}",
            metadata={
                'symbol': signals[0].symbol,
                'aggregation_method': 'majority_vote',
                'component_signals': len(signals),
                'majority_count': len(majority_signals)
            }
        )
