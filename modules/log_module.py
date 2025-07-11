"""
日志模块
负责系统日志记录、交易事件记录等
"""

import os
from loguru import logger
from typing import Dict, Any
import pandas as pd
from .utils import Order, Position

class LogModule:
    """日志管理模块"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_level = config.get('logging', {}).get('level', 'INFO')
        self.log_file = config.get('logging', {}).get('file_path', 'logs/trading.log')
        self.max_file_size = config.get('logging', {}).get('max_file_size', '10MB')
        self.backup_count = config.get('logging', {}).get('backup_count', 5)
        
        # 创建日志目录
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # 配置日志器
        self._setup_logger()
        
        # 交易记录
        self.trade_records = []
        
    def _setup_logger(self):
        """设置日志器"""
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台处理器
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level=self.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True
        )
        
        # 添加文件处理器
        logger.add(
            sink=self.log_file,
            level=self.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=self.max_file_size,
            retention=self.backup_count,
            encoding="utf-8"
        )
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        logger.debug(message, **kwargs)
    
    def log_order(self, order: Order, action: str = "created"):
        """记录订单事件"""
        message = (f"订单{action}: {order.symbol} {order.side.upper()} "
                  f"数量:{order.amount:.6f} 价格:{order.price:.6f} "
                  f"订单ID:{order.order_id} 状态:{order.status}")
        self.info(message)
        
        # 记录到交易记录
        if action == "filled":
            self.trade_records.append({
                'timestamp': order.timestamp,
                'symbol': order.symbol,
                'side': order.side,
                'amount': order.filled_amount,
                'price': order.filled_price,
                'commission': order.commission,
                'order_id': order.order_id
            })
    
    def log_position_update(self, position: Position, current_price: float):
        """记录持仓更新"""
        if not position.is_empty():
            message = (f"持仓更新: {position.symbol} "
                      f"数量:{position.size:.6f} "
                      f"入场价:{position.entry_price:.6f} "
                      f"当前价:{current_price:.6f} "
                      f"未实现盈亏:{position.unrealized_pnl:.2f}")
            self.debug(message)
    
    def log_strategy_signal(self, symbol: str, signal: str, price: float, indicators: Dict[str, float] = None):
        """记录策略信号"""
        message = f"策略信号: {symbol} {signal.upper()} 价格:{price:.6f}"
        if indicators:
            indicator_str = " ".join([f"{k}:{v:.4f}" for k, v in indicators.items()])
            message += f" 指标:[{indicator_str}]"
        self.info(message)
    
    def log_risk_control(self, symbol: str, action: str, reason: str):
        """记录风控事件"""
        message = f"风控触发: {symbol} {action} 原因:{reason}"
        self.warning(message)
    
    def log_backtest_result(self, results: Dict[str, Any]):
        """记录回测结果"""
        self.info("=" * 50)
        self.info("回测结果汇总:")
        self.info(f"总收益率: {results.get('total_return', 0):.2%}")
        self.info(f"年化收益率: {results.get('annual_return', 0):.2%}")
        self.info(f"夏普比率: {results.get('sharpe_ratio', 0):.4f}")
        self.info(f"最大回撤: {results.get('max_drawdown', 0):.2%}")
        self.info(f"胜率: {results.get('win_rate', 0):.2%}")
        self.info(f"总交易次数: {results.get('total_trades', 0)}")
        self.info(f"盈利交易: {results.get('winning_trades', 0)}")
        self.info(f"亏损交易: {results.get('losing_trades', 0)}")
        self.info("=" * 50)
    
    def log_system_status(self, status: str, details: str = ""):
        """记录系统状态"""
        message = f"系统状态: {status}"
        if details:
            message += f" - {details}"
        self.info(message)
    
    def get_trade_records(self) -> pd.DataFrame:
        """获取交易记录"""
        if not self.trade_records:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trade_records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp')
    
    def export_trade_records(self, filepath: str):
        """导出交易记录"""
        df = self.get_trade_records()
        if not df.empty:
            df.to_csv(filepath, index=False)
            self.info(f"交易记录已导出到: {filepath}")
        else:
            self.warning("没有交易记录可导出")
    
    def log_performance_metrics(self, symbol: str, metrics: Dict[str, float]):
        """记录性能指标"""
        message = f"性能指标 {symbol}:"
        for key, value in metrics.items():
            if isinstance(value, float):
                message += f" {key}:{value:.4f}"
            else:
                message += f" {key}:{value}"
        self.info(message)
