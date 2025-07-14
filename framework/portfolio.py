"""
策略组合管理
负责多策略的权重分配、信号合成和组合优化
"""

import asyncio
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from .strategy_base import BaseStrategy, StrategyState
from .signal import Signal, SignalType, SignalAggregator


class PortfolioState(Enum):
    """组合状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    REBALANCING = "rebalancing"
    ERROR = "error"


class StrategyPortfolio:
    """
    策略组合
    管理多个策略的权重分配和信号合成
    """
    
    def __init__(self, name: str, strategies: List[BaseStrategy], 
                 weights: Optional[List[float]] = None, logger=None):
        """
        初始化策略组合
        
        Args:
            name: 组合名称
            strategies: 策略列表
            weights: 策略权重列表，默认等权重
            logger: 日志记录器
        """
        self.name = name
        self.strategies = strategies
        self.weights = weights or [1.0 / len(strategies)] * len(strategies)
        self.logger = logger
        
        # 验证输入
        self._validate_inputs()
        
        # 组合状态
        self.state = PortfolioState.INACTIVE
        self.created_time = datetime.now()
        self.last_rebalance_time = None
        self.last_signal_time = None
        
        # 性能统计
        self.total_signals = 0
        self.signal_history: List[Signal] = []
        self.rebalance_history: List[Dict] = []
        
        # 组合配置
        self.aggregation_method = 'weighted_average'  # 信号聚合方法
        self.min_active_strategies = 1  # 最少活跃策略数
        self.correlation_threshold = 0.8  # 策略相关性阈值
        
        if self.logger:
            self.logger.info(f"📊 策略组合初始化: {self.name}")
    
    def _validate_inputs(self):
        """验证输入参数"""
        if not self.strategies:
            raise ValueError("策略列表不能为空")
        
        if len(self.weights) != len(self.strategies):
            raise ValueError("策略数量与权重数量不匹配")
        
        if abs(sum(self.weights) - 1.0) > 0.01:
            raise ValueError("权重总和必须为1.0")
        
        if any(w < 0 for w in self.weights):
            raise ValueError("权重不能为负数")
    
    async def generate_combined_signal(self, market_data: Dict[str, pd.DataFrame], 
                                     symbol: str) -> Optional[Signal]:
        """
        生成组合信号
        
        Args:
            market_data: 市场数据
            symbol: 交易对
            
        Returns:
            组合信号或None
        """
        try:
            # 收集活跃策略的信号
            active_signals = []
            active_weights = []
            
            for i, strategy in enumerate(self.strategies):
                if strategy.state == StrategyState.ACTIVE:
                    try:
                        # 为单个策略处理数据
                        strategy_signals = await strategy.process_data({symbol: market_data[symbol]})
                        
                        if symbol in strategy_signals:
                            active_signals.append(strategy_signals[symbol])
                            active_weights.append(self.weights[i])
                            
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"❌ 策略 {strategy.name} 信号生成失败: {e}")
                        continue
            
            # 检查是否有足够的活跃策略
            if len(active_signals) < self.min_active_strategies:
                if self.logger:
                    self.logger.warning(f"⚠️ 活跃策略不足: {len(active_signals)}")
                return None
            
            # 标准化权重
            if active_weights:
                total_weight = sum(active_weights)
                active_weights = [w / total_weight for w in active_weights]
            
            # 根据聚合方法合成信号
            if self.aggregation_method == 'weighted_average':
                combined_signal = SignalAggregator.weighted_average(active_signals, active_weights)
            elif self.aggregation_method == 'majority_vote':
                combined_signal = SignalAggregator.majority_vote(active_signals)
            else:
                # 默认使用加权平均
                combined_signal = SignalAggregator.weighted_average(active_signals, active_weights)
            
            # 更新组合信息
            combined_signal.metadata.update({
                'portfolio': self.name,
                'component_strategies': [s.name for s in self.strategies if s.state == StrategyState.ACTIVE],
                'active_weights': active_weights,
                'aggregation_method': self.aggregation_method
            })
            
            # 记录信号
            self.total_signals += 1
            self.signal_history.append(combined_signal)
            self.last_signal_time = datetime.now()
            
            if self.logger:
                self.logger.info(f"🎯 组合信号: {combined_signal}")
            
            return combined_signal
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 组合信号生成失败: {e}")
            return None
    
    def rebalance(self, new_weights: List[float], reason: str = "手动调整") -> Dict[str, Any]:
        """
        重新平衡策略权重
        
        Args:
            new_weights: 新的权重列表
            reason: 调整原因
            
        Returns:
            调整结果
        """
        if len(new_weights) != len(self.strategies):
            raise ValueError("权重数量与策略数量不匹配")
        
        if abs(sum(new_weights) - 1.0) > 0.01:
            raise ValueError("权重总和必须为1.0")
        
        if any(w < 0 for w in new_weights):
            raise ValueError("权重不能为负数")
        
        # 记录调整历史
        old_weights = self.weights.copy()
        self.state = PortfolioState.REBALANCING
        
        rebalance_record = {
            'timestamp': datetime.now().isoformat(),
            'old_weights': old_weights,
            'new_weights': new_weights,
            'reason': reason,
            'weight_changes': [new - old for new, old in zip(new_weights, old_weights)]
        }
        
        # 应用新权重
        self.weights = new_weights
        self.last_rebalance_time = datetime.now()
        self.rebalance_history.append(rebalance_record)
        
        self.state = PortfolioState.ACTIVE
        
        if self.logger:
            self.logger.info(f"⚖️ 组合权重调整: {old_weights} -> {new_weights}")
        
        return rebalance_record
    
    def auto_rebalance(self, performance_data: Dict[str, float]) -> bool:
        """
        基于性能数据自动调整权重
        
        Args:
            performance_data: 策略性能数据 {strategy_name: performance_score}
            
        Returns:
            是否进行了调整
        """
        try:
            # 计算基于性能的权重
            strategy_names = [s.name for s in self.strategies]
            performance_scores = [performance_data.get(name, 0.5) for name in strategy_names]
            
            # 标准化性能分数
            min_score = min(performance_scores)
            max_score = max(performance_scores)
            
            if max_score > min_score:
                normalized_scores = [(score - min_score) / (max_score - min_score) + 0.1 
                                   for score in performance_scores]
            else:
                normalized_scores = [1.0] * len(performance_scores)
            
            # 计算新权重
            total_score = sum(normalized_scores)
            new_weights = [score / total_score for score in normalized_scores]
            
            # 检查是否需要调整（变化超过5%）
            weight_changes = [abs(new - old) for new, old in zip(new_weights, self.weights)]
            if max(weight_changes) > 0.05:
                self.rebalance(new_weights, "基于性能自动调整")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 自动权重调整失败: {e}")
            return False
    
    def calculate_strategy_correlation(self, lookback_days: int = 30) -> Dict[str, Dict[str, float]]:
        """
        计算策略间相关性
        
        Args:
            lookback_days: 回看天数
            
        Returns:
            相关性矩阵
        """
        correlation_matrix = {}
        
        try:
            # 获取最近的信号数据
            cutoff_time = datetime.now() - timedelta(days=lookback_days)
            
            # 为每个策略构建信号序列
            strategy_signals = {}
            for strategy in self.strategies:
                recent_signals = [s for s in strategy.metrics.signal_history 
                                if s.timestamp >= cutoff_time]
                
                # 将信号转换为数值序列
                signal_values = [s.signal_type.value * s.strength for s in recent_signals]
                strategy_signals[strategy.name] = signal_values
            
            # 计算相关性
            strategy_names = list(strategy_signals.keys())
            for i, name1 in enumerate(strategy_names):
                correlation_matrix[name1] = {}
                for j, name2 in enumerate(strategy_names):
                    if i == j:
                        correlation_matrix[name1][name2] = 1.0
                    else:
                        # 计算皮尔逊相关系数
                        signals1 = strategy_signals[name1]
                        signals2 = strategy_signals[name2]
                        
                        if len(signals1) > 1 and len(signals2) > 1:
                            correlation = self._calculate_correlation(signals1, signals2)
                            correlation_matrix[name1][name2] = correlation
                        else:
                            correlation_matrix[name1][name2] = 0.0
            
            return correlation_matrix
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 相关性计算失败: {e}")
            return {}
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """计算两个序列的相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        # 计算均值
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        # 计算协方差和方差
        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        var_x = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        var_y = sum((y[i] - mean_y) ** 2 for i in range(len(y)))
        
        # 计算相关系数
        if var_x > 0 and var_y > 0:
            correlation = covariance / (var_x * var_y) ** 0.5
            return max(-1.0, min(1.0, correlation))  # 限制在[-1, 1]范围内
        else:
            return 0.0
    
    def get_diversification_score(self) -> float:
        """
        计算组合分散化得分
        
        Returns:
            分散化得分 (0-1，越高越好)
        """
        try:
            correlation_matrix = self.calculate_strategy_correlation()
            
            if not correlation_matrix:
                return 0.5  # 默认中等分散化
            
            # 计算平均相关性
            total_correlation = 0
            count = 0
            
            strategy_names = list(correlation_matrix.keys())
            for i, name1 in enumerate(strategy_names):
                for j, name2 in enumerate(strategy_names):
                    if i != j:
                        total_correlation += abs(correlation_matrix[name1][name2])
                        count += 1
            
            if count > 0:
                avg_correlation = total_correlation / count
                # 相关性越低，分散化得分越高
                diversification_score = 1.0 - avg_correlation
                return max(0.0, min(1.0, diversification_score))
            else:
                return 0.5
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 分散化得分计算失败: {e}")
            return 0.5
    
    def activate(self):
        """激活组合"""
        self.state = PortfolioState.ACTIVE
        if self.logger:
            self.logger.info(f"✅ 组合激活: {self.name}")
    
    def deactivate(self):
        """停用组合"""
        self.state = PortfolioState.INACTIVE
        if self.logger:
            self.logger.info(f"⏹️ 组合停用: {self.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取组合状态"""
        active_strategies = sum(1 for s in self.strategies if s.state == StrategyState.ACTIVE)
        
        return {
            'name': self.name,
            'state': self.state.value,
            'strategies': [s.name for s in self.strategies],
            'weights': self.weights,
            'active_strategies': active_strategies,
            'total_strategies': len(self.strategies),
            'created_time': self.created_time.isoformat(),
            'last_rebalance_time': self.last_rebalance_time.isoformat() if self.last_rebalance_time else None,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'total_signals': self.total_signals,
            'diversification_score': self.get_diversification_score(),
            'aggregation_method': self.aggregation_method,
            'rebalance_count': len(self.rebalance_history)
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取组合性能报告"""
        status = self.get_status()
        
        # 计算信号分布
        signal_distribution = {}
        for signal in self.signal_history:
            signal_type = signal.signal_type.name
            signal_distribution[signal_type] = signal_distribution.get(signal_type, 0) + 1
        
        # 计算平均信号强度
        avg_strength = 0.0
        if self.signal_history:
            avg_strength = sum(s.strength for s in self.signal_history) / len(self.signal_history)
        
        return {
            'portfolio_name': self.name,
            'status': status,
            'signal_distribution': signal_distribution,
            'avg_signal_strength': round(avg_strength, 3),
            'strategy_weights': dict(zip([s.name for s in self.strategies], self.weights)),
            'rebalance_history': self.rebalance_history[-5:],  # 最近5次调整
            'correlation_matrix': self.calculate_strategy_correlation()
        }
    
    def __str__(self):
        return f"StrategyPortfolio({self.name}, strategies={len(self.strategies)}, state={self.state.value})"
    
    def __repr__(self):
        return self.__str__()
