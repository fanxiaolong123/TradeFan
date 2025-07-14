"""
策略配置模板
定义各种策略类型的默认配置参数
从core/strategy_examples.py移动到strategies/
"""

# 策略配置模板字典
STRATEGY_TEMPLATES = {
    'trend_following': {
        'description': '趋势跟踪策略，基于EMA交叉和RSI过滤',
        'parameters': {
            'fast_ema': 8,
            'slow_ema': 21,
            'rsi_threshold': 50,
            'rsi_overbought': 80,
            'rsi_oversold': 20
        },
        'timeframes': ['1h', '4h'],
        'min_data_points': 50,
        'signal_cooldown': 300,  # 5分钟
        'max_signals_per_hour': 6,
        'risk_settings': {
            'min_signal_strength': 0.3,
            'stop_loss': 0.02,
            'take_profit': 0.04
        }
    },
    
    'mean_reversion': {
        'description': '均值回归策略，基于布林带和RSI超买超卖',
        'parameters': {
            'bb_period': 20,
            'bb_std': 2.0,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'bb_threshold_low': 0.15,
            'bb_threshold_high': 0.85
        },
        'timeframes': ['1h'],
        'min_data_points': 30,
        'signal_cooldown': 600,  # 10分钟
        'max_signals_per_hour': 4,
        'risk_settings': {
            'min_signal_strength': 0.4,
            'stop_loss': 0.015,
            'take_profit': 0.03
        }
    },
    
    'breakout': {
        'description': '突破策略，基于价格通道突破和成交量确认',
        'parameters': {
            'lookback_period': 24,
            'min_channel_width': 0.025,
            'volume_confirmation': True,
            'volume_multiplier': 1.5
        },
        'timeframes': ['4h', '1d'],
        'min_data_points': 40,
        'signal_cooldown': 1800,  # 30分钟
        'max_signals_per_hour': 2,
        'risk_settings': {
            'min_signal_strength': 0.5,
            'stop_loss': 0.025,
            'take_profit': 0.05
        }
    },
    
    'momentum': {
        'description': '动量策略，基于价格动量和ROC指标',
        'parameters': {
            'momentum_period': 12,
            'roc_period': 14,
            'momentum_threshold': 0.025,
            'rsi_filter': True,
            'rsi_min': 35,
            'rsi_max': 65
        },
        'timeframes': ['1h'],
        'min_data_points': 25,
        'signal_cooldown': 300,  # 5分钟
        'max_signals_per_hour': 8,
        'risk_settings': {
            'min_signal_strength': 0.3,
            'stop_loss': 0.02,
            'take_profit': 0.04
        }
    },
    
    'scalping': {
        'description': '剥头皮策略，基于短期EMA和价格偏离',
        'parameters': {
            'fast_ema': 5,
            'slow_ema': 13,
            'ema_diff_threshold': 0.001,
            'price_deviation_threshold': 0.002,
            'min_volatility': 0.005,
            'max_volatility': 0.02
        },
        'timeframes': ['5m', '15m'],
        'min_data_points': 20,
        'signal_cooldown': 60,   # 1分钟
        'max_signals_per_hour': 20,
        'risk_settings': {
            'min_signal_strength': 0.2,
            'stop_loss': 0.008,
            'take_profit': 0.015
        }
    },
    
    'conservative': {
        'description': '保守策略，低频率高质量信号',
        'parameters': {
            'fast_ema': 12,
            'slow_ema': 26,
            'rsi_threshold': 50,
            'confirmation_required': True
        },
        'timeframes': ['4h', '1d'],
        'min_data_points': 60,
        'signal_cooldown': 3600,  # 1小时
        'max_signals_per_hour': 1,
        'risk_settings': {
            'min_signal_strength': 0.6,
            'stop_loss': 0.015,
            'take_profit': 0.06
        }
    },
    
    'aggressive': {
        'description': '激进策略，高频率交易',
        'parameters': {
            'fast_ema': 5,
            'slow_ema': 15,
            'rsi_threshold': 50,
            'quick_signals': True
        },
        'timeframes': ['15m', '30m'],
        'min_data_points': 30,
        'signal_cooldown': 120,   # 2分钟
        'max_signals_per_hour': 15,
        'risk_settings': {
            'min_signal_strength': 0.25,
            'stop_loss': 0.01,
            'take_profit': 0.025
        }
    }
}


def get_strategy_template(strategy_type: str) -> dict:
    """
    获取策略配置模板
    
    Args:
        strategy_type: 策略类型名称
        
    Returns:
        策略配置模板字典
    """
    return STRATEGY_TEMPLATES.get(strategy_type, STRATEGY_TEMPLATES['trend_following'])


def list_available_templates() -> list:
    """
    列出所有可用的策略模板
    
    Returns:
        策略类型列表
    """
    return list(STRATEGY_TEMPLATES.keys())


def create_custom_template(name: str, base_template: str, 
                          custom_params: dict) -> dict:
    """
    创建自定义策略模板
    
    Args:
        name: 自定义模板名称
        base_template: 基础模板名称
        custom_params: 自定义参数
        
    Returns:
        自定义策略模板
    """
    if base_template not in STRATEGY_TEMPLATES:
        raise ValueError(f"基础模板不存在: {base_template}")
    
    # 复制基础模板
    custom_template = STRATEGY_TEMPLATES[base_template].copy()
    
    # 更新自定义参数
    if 'parameters' in custom_params:
        custom_template['parameters'].update(custom_params['parameters'])
    
    if 'risk_settings' in custom_params:
        custom_template['risk_settings'].update(custom_params['risk_settings'])
    
    # 更新其他配置
    for key, value in custom_params.items():
        if key not in ['parameters', 'risk_settings']:
            custom_template[key] = value
    
    # 添加到模板字典
    STRATEGY_TEMPLATES[name] = custom_template
    
    return custom_template


def validate_template(template: dict) -> bool:
    """
    验证策略模板的完整性
    
    Args:
        template: 策略模板字典
        
    Returns:
        是否有效
    """
    required_fields = [
        'parameters', 'timeframes', 'min_data_points',
        'signal_cooldown', 'max_signals_per_hour', 'risk_settings'
    ]
    
    for field in required_fields:
        if field not in template:
            return False
    
    # 检查风险设置
    risk_required = ['min_signal_strength', 'stop_loss', 'take_profit']
    for field in risk_required:
        if field not in template['risk_settings']:
            return False
    
    return True
