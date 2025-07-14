"""
日志管理器
标准化日志格式、文件管理、不同级别输出
支持多种输出方式：文件、控制台、远程日志服务
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import traceback


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        # 添加颜色
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class TradingLogFilter(logging.Filter):
    """交易专用日志过滤器"""
    
    def __init__(self, include_patterns: List[str] = None, exclude_patterns: List[str] = None):
        super().__init__()
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
    
    def filter(self, record):
        message = record.getMessage()
        
        # 排除模式检查
        for pattern in self.exclude_patterns:
            if pattern.lower() in message.lower():
                return False
        
        # 包含模式检查（如果指定了包含模式）
        if self.include_patterns:
            for pattern in self.include_patterns:
                if pattern.lower() in message.lower():
                    return True
            return False
        
        return True


class LoggerManager:
    """统一日志管理器"""
    
    def __init__(self, name: str = "TradeFan", log_dir: str = "logs", 
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化日志管理器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录
            config: 日志配置
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.config = config or {}
        self.loggers = {}  # 缓存创建的日志器
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认配置
        self.default_config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'file_max_size': 10 * 1024 * 1024,  # 10MB
            'file_backup_count': 5,
            'console_output': True,
            'file_output': True,
            'colored_output': True
        }
        
        # 合并配置
        self.effective_config = {**self.default_config, **self.config}
    
    def create_logger(self, logger_name: str, module_name: str = None, 
                     custom_config: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """
        创建专用日志器
        
        Args:
            logger_name: 日志器名称
            module_name: 模块名称
            custom_config: 自定义配置
            
        Returns:
            配置好的日志器
        """
        full_name = f"{self.name}.{logger_name}" if logger_name != self.name else self.name
        
        # 检查缓存
        if full_name in self.loggers:
            return self.loggers[full_name]
        
        # 合并配置
        config = {**self.effective_config}
        if custom_config:
            config.update(custom_config)
        
        # 创建日志器
        logger = logging.getLogger(full_name)
        logger.setLevel(getattr(logging, config['level'].upper()))
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=config['format'],
            datefmt=config['date_format']
        )
        
        colored_formatter = ColoredFormatter(
            fmt=config['format'],
            datefmt=config['date_format']
        )
        
        # 控制台输出
        if config['console_output']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, config['level'].upper()))
            
            if config['colored_output'] and sys.stdout.isatty():
                console_handler.setFormatter(colored_formatter)
            else:
                console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
        
        # 文件输出
        if config['file_output']:
            # 主日志文件
            log_file = self.log_dir / f"{logger_name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=config['file_max_size'],
                backupCount=config['file_backup_count'],
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, config['level'].upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # 错误日志文件
            error_log_file = self.log_dir / f"{logger_name}_error_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=config['file_max_size'],
                backupCount=config['file_backup_count'],
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            logger.addHandler(error_handler)
        
        # 添加过滤器
        if 'filters' in config:
            for filter_config in config['filters']:
                log_filter = TradingLogFilter(
                    include_patterns=filter_config.get('include', []),
                    exclude_patterns=filter_config.get('exclude', [])
                )
                logger.addFilter(log_filter)
        
        # 缓存日志器
        self.loggers[full_name] = logger
        
        logger.info(f"📝 日志器初始化完成: {full_name}")
        return logger
    
    def get_trading_logger(self, strategy_name: str = None) -> logging.Logger:
        """
        获取交易专用日志器
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            交易日志器
        """
        logger_name = f"trading.{strategy_name}" if strategy_name else "trading"
        
        # 交易日志特殊配置
        trading_config = {
            'filters': [{
                'include': ['订单', '交易', '信号', '仓位', '盈亏', 'order', 'trade', 'signal', 'position', 'pnl'],
                'exclude': ['debug', 'heartbeat']
            }]
        }
        
        return self.create_logger(logger_name, custom_config=trading_config)
    
    def get_api_logger(self) -> logging.Logger:
        """获取API专用日志器"""
        api_config = {
            'filters': [{
                'include': ['api', 'request', 'response', 'error'],
                'exclude': ['heartbeat', 'ping']
            }]
        }
        
        return self.create_logger("api", custom_config=api_config)
    
    def get_strategy_logger(self, strategy_name: str) -> logging.Logger:
        """
        获取策略专用日志器
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略日志器
        """
        return self.create_logger(f"strategy.{strategy_name}")
    
    def get_risk_logger(self) -> logging.Logger:
        """获取风险管理专用日志器"""
        risk_config = {
            'filters': [{
                'include': ['风险', '止损', '止盈', '仓位', 'risk', 'stop', 'position'],
                'exclude': []
            }]
        }
        
        return self.create_logger("risk", custom_config=risk_config)
    
    def log_trade_event(self, logger: logging.Logger, event_type: str, 
                       symbol: str, data: Dict[str, Any]):
        """
        记录交易事件
        
        Args:
            logger: 日志器
            event_type: 事件类型 ('signal', 'order', 'fill', 'error')
            symbol: 交易对
            data: 事件数据
        """
        timestamp = datetime.now().isoformat()
        
        # 构建结构化日志消息
        log_data = {
            'timestamp': timestamp,
            'event_type': event_type,
            'symbol': symbol,
            **data
        }
        
        # 根据事件类型选择日志级别
        level_map = {
            'signal': logging.INFO,
            'order': logging.INFO,
            'fill': logging.INFO,
            'error': logging.ERROR,
            'warning': logging.WARNING
        }
        
        level = level_map.get(event_type, logging.INFO)
        
        # 格式化消息
        if event_type == 'signal':
            message = f"📊 交易信号 | {symbol} | {data.get('signal', 'N/A')} | 价格: {data.get('price', 'N/A')}"
        elif event_type == 'order':
            message = f"📝 订单操作 | {symbol} | {data.get('side', 'N/A')} | 数量: {data.get('quantity', 'N/A')} | 价格: {data.get('price', 'N/A')}"
        elif event_type == 'fill':
            message = f"✅ 订单成交 | {symbol} | {data.get('side', 'N/A')} | 数量: {data.get('quantity', 'N/A')} | 价格: {data.get('price', 'N/A')}"
        elif event_type == 'error':
            message = f"❌ 交易错误 | {symbol} | {data.get('error', 'N/A')}"
        else:
            message = f"📋 交易事件 | {event_type} | {symbol} | {json.dumps(data, ensure_ascii=False)}"
        
        logger.log(level, message)
        
        # 同时记录结构化数据到专门的文件
        self._log_structured_data(event_type, log_data)
    
    def _log_structured_data(self, event_type: str, data: Dict[str, Any]):
        """记录结构化数据到JSON文件"""
        try:
            json_log_file = self.log_dir / f"structured_{event_type}_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            with open(json_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
                
        except Exception as e:
            # 避免日志记录本身出错影响主程序
            print(f"结构化日志记录失败: {e}")
    
    def log_exception(self, logger: logging.Logger, exception: Exception, 
                     context: str = None):
        """
        记录异常信息
        
        Args:
            logger: 日志器
            exception: 异常对象
            context: 上下文信息
        """
        error_info = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'context': context or 'Unknown'
        }
        
        message = f"💥 异常发生 | {context or 'Unknown'} | {type(exception).__name__}: {str(exception)}"
        logger.error(message)
        
        # 记录详细的异常信息
        self._log_structured_data('exception', error_info)
    
    def create_performance_logger(self) -> logging.Logger:
        """创建性能监控日志器"""
        perf_config = {
            'level': 'DEBUG',
            'filters': [{
                'include': ['performance', 'timing', 'memory', 'cpu'],
                'exclude': []
            }]
        }
        
        return self.create_logger("performance", custom_config=perf_config)
    
    def log_performance_metric(self, logger: logging.Logger, metric_name: str, 
                              value: float, unit: str = None, context: Dict[str, Any] = None):
        """
        记录性能指标
        
        Args:
            logger: 日志器
            metric_name: 指标名称
            value: 指标值
            unit: 单位
            context: 上下文信息
        """
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'metric_name': metric_name,
            'value': value,
            'unit': unit or '',
            'context': context or {}
        }
        
        unit_str = f" {unit}" if unit else ""
        message = f"📈 性能指标 | {metric_name}: {value}{unit_str}"
        
        logger.info(message)
        self._log_structured_data('performance', perf_data)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        清理旧日志文件
        
        Args:
            days_to_keep: 保留天数
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            
            cleaned_count = 0
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"🧹 清理了 {cleaned_count} 个旧日志文件")
                
        except Exception as e:
            print(f"日志清理失败: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = {
            'log_dir': str(self.log_dir),
            'active_loggers': len(self.loggers),
            'logger_names': list(self.loggers.keys()),
            'log_files': [],
            'total_size': 0
        }
        
        try:
            for log_file in self.log_dir.glob("*.log*"):
                file_size = log_file.stat().st_size
                stats['log_files'].append({
                    'name': log_file.name,
                    'size': file_size,
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
                stats['total_size'] += file_size
            
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
            
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    def set_log_level(self, logger_name: str, level: str):
        """
        动态设置日志级别
        
        Args:
            logger_name: 日志器名称
            level: 日志级别
        """
        if logger_name in self.loggers:
            logger = self.loggers[logger_name]
            logger.setLevel(getattr(logging, level.upper()))
            logger.info(f"📝 日志级别已更改为: {level}")
    
    def __str__(self):
        return f"LoggerManager({self.name}, loggers={len(self.loggers)})"
    
    def __repr__(self):
        return self.__str__()
