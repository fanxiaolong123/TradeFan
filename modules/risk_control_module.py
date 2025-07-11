"""
风险控制模块
负责仓位管理、止损止盈、最大回撤控制等风险管理功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from .utils import Position, Order, OrderType

class RiskControlModule:
    """风险控制模块"""
    
    def __init__(self, config: Dict, logger=None):
        self.config = config
        self.logger = logger
        
        # 风险参数
        risk_config = config.get('risk_control', {})
        self.max_position_size = risk_config.get('max_position_size', 0.1)
        self.max_total_position = risk_config.get('max_total_position', 0.8)
        self.max_drawdown = risk_config.get('max_drawdown', 0.2)
        self.stop_loss = risk_config.get('stop_loss', 0.02)
        self.take_profit = risk_config.get('take_profit', 0.04)
        self.initial_capital = risk_config.get('initial_capital', 10000)
        
        # 当前状态
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.positions = {}  # symbol -> Position
        self.daily_pnl = []
        self.equity_curve = [self.initial_capital]
        
        if self.logger:
            self.logger.info(f"风险控制模块初始化完成 - 初始资金: {self.initial_capital}")
    
    def check_position_limit(self, symbol: str, order_amount: float, 
                           current_price: float) -> Tuple[bool, str, float]:
        """
        检查仓位限制
        
        Args:
            symbol: 交易对
            order_amount: 订单数量
            current_price: 当前价格
            
        Returns:
            (是否通过, 原因, 调整后的数量)
        """
        try:
            # 计算订单价值
            order_value = abs(order_amount) * current_price
            
            # 检查单个币种仓位限制
            max_single_value = self.current_capital * self.max_position_size
            if order_value > max_single_value:
                adjusted_amount = max_single_value / current_price
                if abs(adjusted_amount) < abs(order_amount):
                    return False, f"超过单币种仓位限制({self.max_position_size:.1%})", adjusted_amount
            
            # 检查总仓位限制
            total_position_value = self._calculate_total_position_value()
            if (total_position_value + order_value) > (self.current_capital * self.max_total_position):
                return False, f"超过总仓位限制({self.max_total_position:.1%})", 0
            
            # 检查资金充足性
            required_margin = order_value * 0.1  # 假设10%保证金
            if required_margin > self._get_available_balance():
                return False, "可用资金不足", 0
            
            return True, "通过风控检查", order_amount
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"仓位限制检查失败: {e}")
            return False, f"风控检查异常: {e}", 0
    
    def check_drawdown_limit(self) -> Tuple[bool, str]:
        """检查最大回撤限制"""
        try:
            current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            
            if current_drawdown > self.max_drawdown:
                return False, f"触发最大回撤限制({current_drawdown:.2%} > {self.max_drawdown:.2%})"
            
            return True, "回撤检查通过"
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"回撤检查失败: {e}")
            return False, f"回撤检查异常: {e}"
    
    def calculate_position_size(self, symbol: str, signal_strength: float, 
                              current_price: float, volatility: float = None) -> float:
        """
        计算仓位大小
        
        Args:
            symbol: 交易对
            signal_strength: 信号强度 (0-1)
            current_price: 当前价格
            volatility: 波动率
            
        Returns:
            建议仓位大小
        """
        try:
            # 基础仓位大小
            base_position_value = self.current_capital * self.max_position_size
            
            # 根据信号强度调整
            adjusted_position_value = base_position_value * signal_strength
            
            # 根据波动率调整（如果提供）
            if volatility is not None and volatility > 0:
                # 波动率越高，仓位越小
                volatility_adjustment = min(1.0, 0.02 / volatility)  # 假设目标波动率为2%
                adjusted_position_value *= volatility_adjustment
            
            # 转换为数量
            position_size = adjusted_position_value / current_price
            
            # 确保不超过限制
            max_size = (self.current_capital * self.max_position_size) / current_price
            position_size = min(position_size, max_size)
            
            return position_size
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算仓位大小失败: {e}")
            return 0
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> List[Dict]:
        """
        检查止损止盈条件
        
        Args:
            symbol: 交易对
            current_price: 当前价格
            
        Returns:
            需要执行的订单列表
        """
        orders = []
        
        if symbol not in self.positions:
            return orders
        
        position = self.positions[symbol]
        if position.is_empty():
            return orders
        
        try:
            entry_price = position.entry_price
            position_size = position.size
            
            # 计算盈亏比例
            if position.is_long():
                pnl_ratio = (current_price - entry_price) / entry_price
                
                # 止损检查
                if pnl_ratio <= -self.stop_loss:
                    orders.append({
                        'symbol': symbol,
                        'side': OrderType.SELL,
                        'amount': abs(position_size),
                        'price': current_price,
                        'reason': f'止损触发 (亏损{pnl_ratio:.2%})'
                    })
                
                # 止盈检查
                elif pnl_ratio >= self.take_profit:
                    orders.append({
                        'symbol': symbol,
                        'side': OrderType.SELL,
                        'amount': abs(position_size),
                        'price': current_price,
                        'reason': f'止盈触发 (盈利{pnl_ratio:.2%})'
                    })
            
            elif position.is_short():
                pnl_ratio = (entry_price - current_price) / entry_price
                
                # 止损检查
                if pnl_ratio <= -self.stop_loss:
                    orders.append({
                        'symbol': symbol,
                        'side': OrderType.BUY,
                        'amount': abs(position_size),
                        'price': current_price,
                        'reason': f'止损触发 (亏损{pnl_ratio:.2%})'
                    })
                
                # 止盈检查
                elif pnl_ratio >= self.take_profit:
                    orders.append({
                        'symbol': symbol,
                        'side': OrderType.BUY,
                        'amount': abs(position_size),
                        'price': current_price,
                        'reason': f'止盈触发 (盈利{pnl_ratio:.2%})'
                    })
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"止损止盈检查失败: {e}")
        
        return orders
    
    def update_position(self, symbol: str, side: str, amount: float, price: float):
        """更新持仓"""
        try:
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
            
            position = self.positions[symbol]
            
            if side == OrderType.BUY:
                if position.is_short():
                    # 平空仓
                    if amount >= abs(position.size):
                        # 完全平仓或反向开仓
                        remaining = amount - abs(position.size)
                        position.realized_pnl += (position.entry_price - price) * abs(position.size)
                        
                        if remaining > 0:
                            # 反向开多仓
                            position.size = remaining
                            position.entry_price = price
                        else:
                            # 完全平仓
                            position.size = 0
                            position.entry_price = 0
                    else:
                        # 部分平仓
                        position.size += amount
                        position.realized_pnl += (position.entry_price - price) * amount
                else:
                    # 开多仓或加仓
                    if position.is_empty():
                        position.size = amount
                        position.entry_price = price
                    else:
                        # 加仓，重新计算平均成本
                        total_cost = position.size * position.entry_price + amount * price
                        position.size += amount
                        position.entry_price = total_cost / position.size
            
            elif side == OrderType.SELL:
                if position.is_long():
                    # 平多仓
                    if amount >= position.size:
                        # 完全平仓或反向开仓
                        remaining = amount - position.size
                        position.realized_pnl += (price - position.entry_price) * position.size
                        
                        if remaining > 0:
                            # 反向开空仓
                            position.size = -remaining
                            position.entry_price = price
                        else:
                            # 完全平仓
                            position.size = 0
                            position.entry_price = 0
                    else:
                        # 部分平仓
                        position.size -= amount
                        position.realized_pnl += (price - position.entry_price) * amount
                else:
                    # 开空仓或加仓
                    if position.is_empty():
                        position.size = -amount
                        position.entry_price = price
                    else:
                        # 加仓，重新计算平均成本
                        total_cost = abs(position.size) * position.entry_price + amount * price
                        position.size -= amount
                        position.entry_price = total_cost / abs(position.size)
            
            if self.logger:
                self.logger.debug(f"持仓更新: {symbol} 数量:{position.size:.6f} 成本:{position.entry_price:.6f}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"更新持仓失败: {e}")
    
    def update_capital(self, pnl: float):
        """更新资金"""
        self.current_capital += pnl
        self.peak_capital = max(self.peak_capital, self.current_capital)
        self.equity_curve.append(self.current_capital)
        
        if pnl != 0:
            self.daily_pnl.append(pnl)
    
    def get_portfolio_status(self) -> Dict:
        """获取投资组合状态"""
        try:
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            
            return {
                'current_capital': self.current_capital,
                'initial_capital': self.initial_capital,
                'peak_capital': self.peak_capital,
                'total_pnl': total_pnl,
                'unrealized_pnl': total_unrealized_pnl,
                'realized_pnl': total_realized_pnl,
                'total_return': (self.current_capital - self.initial_capital) / self.initial_capital,
                'current_drawdown': current_drawdown,
                'max_drawdown_limit': self.max_drawdown,
                'position_count': len([p for p in self.positions.values() if not p.is_empty()]),
                'total_position_value': self._calculate_total_position_value(),
                'available_balance': self._get_available_balance()
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取投资组合状态失败: {e}")
            return {}
    
    def _calculate_total_position_value(self) -> float:
        """计算总持仓价值"""
        # 这里简化处理，实际应该根据当前价格计算
        return sum(abs(pos.size) * pos.entry_price for pos in self.positions.values() if not pos.is_empty())
    
    def _get_available_balance(self) -> float:
        """获取可用余额"""
        used_margin = self._calculate_total_position_value() * 0.1  # 假设10%保证金
        return max(0, self.current_capital - used_margin)
    
    def reset(self):
        """重置风控状态（用于回测）"""
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.positions = {}
        self.daily_pnl = []
        self.equity_curve = [self.initial_capital]
    
    def get_position(self, symbol: str) -> Position:
        """获取持仓信息"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]
    
    def calculate_risk_metrics(self) -> Dict:
        """计算风险指标"""
        try:
            if len(self.equity_curve) < 2:
                return {}
            
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            
            if len(returns) == 0:
                return {}
            
            # 计算各种风险指标
            volatility = returns.std() * np.sqrt(252)  # 年化波动率
            sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            
            # 最大回撤
            cumulative = (1 + returns).cumprod()
            peak = cumulative.expanding().max()
            drawdown = (cumulative - peak) / peak
            max_drawdown = drawdown.min()
            
            # VaR (Value at Risk)
            var_95 = returns.quantile(0.05)
            var_99 = returns.quantile(0.01)
            
            return {
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'var_95': var_95,
                'var_99': var_99,
                'win_rate': (returns > 0).mean(),
                'avg_return': returns.mean(),
                'avg_win': returns[returns > 0].mean() if (returns > 0).any() else 0,
                'avg_loss': returns[returns < 0].mean() if (returns < 0).any() else 0
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"计算风险指标失败: {e}")
            return {}
