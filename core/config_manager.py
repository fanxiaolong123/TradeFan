"""
配置管理器
统一管理所有配置文件，支持环境变量替换、配置验证、多环境配置
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, List, Union
import logging
from pathlib import Path
import re
from datetime import datetime


class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_dir: str = "config", logger: Optional[logging.Logger] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
            logger: 日志记录器
        """
        self.config_dir = Path(config_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.configs = {}  # 缓存已加载的配置
        self.env_pattern = re.compile(r'\$\{([^}]+)\}')  # 环境变量模式
        
        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"📁 初始化配置管理器: {self.config_dir}")
    
    def _replace_env_vars(self, value: Any) -> Any:
        """
        递归替换配置中的环境变量
        
        Args:
            value: 配置值
            
        Returns:
            替换后的值
        """
        if isinstance(value, str):
            # 查找并替换环境变量
            def replace_match(match):
                env_var = match.group(1)
                # 支持默认值语法: ${VAR:default_value}
                if ':' in env_var:
                    var_name, default_value = env_var.split(':', 1)
                    return os.getenv(var_name.strip(), default_value.strip())
                else:
                    env_value = os.getenv(env_var.strip())
                    if env_value is None:
                        self.logger.warning(f"⚠️ 环境变量未设置: {env_var}")
                        return match.group(0)  # 保持原样
                    return env_value
            
            return self.env_pattern.sub(replace_match, value)
        
        elif isinstance(value, dict):
            return {k: self._replace_env_vars(v) for k, v in value.items()}
        
        elif isinstance(value, list):
            return [self._replace_env_vars(item) for item in value]
        
        else:
            return value
    
    def _validate_config_structure(self, config: Dict[str, Any], config_type: str) -> bool:
        """
        验证配置结构
        
        Args:
            config: 配置字典
            config_type: 配置类型
            
        Returns:
            是否有效
        """
        required_sections = {
            'trading': ['api', 'trading', 'risk_management'],
            'backtest': ['data_source', 'strategy', 'backtest'],
            'production': ['api', 'trading', 'risk_management', 'monitoring'],
            'scalping': ['api', 'trading', 'scalping', 'risk_management']
        }
        
        if config_type not in required_sections:
            self.logger.warning(f"⚠️ 未知配置类型: {config_type}")
            return True  # 未知类型不验证
        
        missing_sections = []
        for section in required_sections[config_type]:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            self.logger.error(f"❌ 配置缺少必需部分: {missing_sections}")
            return False
        
        # API配置验证
        if 'api' in config:
            api_config = config['api']
            required_api_fields = ['api_key', 'api_secret', 'base_url']
            
            for field in required_api_fields:
                if field not in api_config or not api_config[field]:
                    self.logger.error(f"❌ API配置缺少字段: {field}")
                    return False
        
        # 交易配置验证
        if 'trading' in config:
            trading_config = config['trading']
            if 'symbols' not in trading_config or not trading_config['symbols']:
                self.logger.error("❌ 交易配置缺少交易对")
                return False
        
        return True
    
    def load_config(self, config_name: str, validate: bool = True, 
                   cache: bool = True) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_name: 配置文件名（不含扩展名）
            validate: 是否验证配置
            cache: 是否缓存配置
            
        Returns:
            配置字典
        """
        # 检查缓存
        if cache and config_name in self.configs:
            self.logger.debug(f"📋 使用缓存配置: {config_name}")
            return self.configs[config_name].copy()
        
        # 支持多种文件格式
        config_file = None
        for ext in ['.yaml', '.yml', '.json']:
            potential_file = self.config_dir / f"{config_name}{ext}"
            if potential_file.exists():
                config_file = potential_file
                break
        
        if not config_file:
            raise FileNotFoundError(f"配置文件不存在: {config_name}")
        
        self.logger.info(f"📖 加载配置文件: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    config = yaml.safe_load(f)
            
            # 替换环境变量
            config = self._replace_env_vars(config)
            
            # 添加元数据
            config['_meta'] = {
                'config_name': config_name,
                'config_file': str(config_file),
                'loaded_at': datetime.now().isoformat(),
                'version': config.get('version', '1.0.0')
            }
            
            # 验证配置
            if validate:
                config_type = self._detect_config_type(config_name, config)
                if not self._validate_config_structure(config, config_type):
                    raise ValueError(f"配置验证失败: {config_name}")
            
            # 缓存配置
            if cache:
                self.configs[config_name] = config.copy()
            
            self.logger.info(f"✅ 配置加载成功: {config_name}")
            return config
            
        except Exception as e:
            self.logger.error(f"❌ 配置加载失败: {config_name} - {e}")
            raise
    
    def _detect_config_type(self, config_name: str, config: Dict[str, Any]) -> str:
        """
        检测配置类型
        
        Args:
            config_name: 配置名称
            config: 配置内容
            
        Returns:
            配置类型
        """
        # 根据文件名判断
        if 'production' in config_name.lower():
            return 'production'
        elif 'scalping' in config_name.lower():
            return 'scalping'
        elif 'backtest' in config_name.lower():
            return 'backtest'
        elif 'trading' in config_name.lower():
            return 'trading'
        
        # 根据配置内容判断
        if 'scalping' in config:
            return 'scalping'
        elif 'backtest' in config:
            return 'backtest'
        elif 'monitoring' in config and 'api' in config:
            return 'production'
        else:
            return 'trading'
    
    def save_config(self, config_name: str, config: Dict[str, Any], 
                   format: str = 'yaml') -> bool:
        """
        保存配置文件
        
        Args:
            config_name: 配置名称
            config: 配置内容
            format: 文件格式 ('yaml', 'json')
            
        Returns:
            是否保存成功
        """
        try:
            # 移除元数据
            config_to_save = config.copy()
            config_to_save.pop('_meta', None)
            
            # 确定文件路径
            ext = '.yaml' if format == 'yaml' else '.json'
            config_file = self.config_dir / f"{config_name}{ext}"
            
            # 备份现有文件
            if config_file.exists():
                backup_file = config_file.with_suffix(f"{ext}.backup")
                config_file.rename(backup_file)
                self.logger.info(f"📦 备份配置文件: {backup_file}")
            
            # 保存新配置
            with open(config_file, 'w', encoding='utf-8') as f:
                if format == 'json':
                    json.dump(config_to_save, f, indent=2, ensure_ascii=False)
                else:
                    yaml.dump(config_to_save, f, default_flow_style=False, 
                             allow_unicode=True, indent=2)
            
            # 更新缓存
            self.configs[config_name] = config.copy()
            
            self.logger.info(f"💾 配置保存成功: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 配置保存失败: {config_name} - {e}")
            return False
    
    def get_config_value(self, config_name: str, key_path: str, 
                        default: Any = None) -> Any:
        """
        获取配置中的特定值
        
        Args:
            config_name: 配置名称
            key_path: 键路径，用点分隔 (如: 'api.api_key')
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            config = self.load_config(config_name)
            
            # 按路径获取值
            value = config
            for key in key_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception as e:
            self.logger.error(f"❌ 获取配置值失败: {config_name}.{key_path} - {e}")
            return default
    
    def set_config_value(self, config_name: str, key_path: str, value: Any) -> bool:
        """
        设置配置中的特定值
        
        Args:
            config_name: 配置名称
            key_path: 键路径
            value: 新值
            
        Returns:
            是否设置成功
        """
        try:
            config = self.load_config(config_name)
            
            # 按路径设置值
            current = config
            keys = key_path.split('.')
            
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            current[keys[-1]] = value
            
            # 保存配置
            return self.save_config(config_name, config)
            
        except Exception as e:
            self.logger.error(f"❌ 设置配置值失败: {config_name}.{key_path} - {e}")
            return False
    
    def list_configs(self) -> List[str]:
        """列出所有可用配置"""
        configs = []
        for file_path in self.config_dir.glob('*.yaml'):
            configs.append(file_path.stem)
        for file_path in self.config_dir.glob('*.yml'):
            configs.append(file_path.stem)
        for file_path in self.config_dir.glob('*.json'):
            configs.append(file_path.stem)
        
        return sorted(list(set(configs)))
    
    def validate_api_credentials(self, config_name: str) -> bool:
        """
        验证API凭证
        
        Args:
            config_name: 配置名称
            
        Returns:
            凭证是否有效
        """
        try:
            api_key = self.get_config_value(config_name, 'api.api_key')
            api_secret = self.get_config_value(config_name, 'api.api_secret')
            
            if not api_key or not api_secret:
                self.logger.error("❌ API凭证为空")
                return False
            
            # 检查凭证格式
            if len(api_key) < 32 or len(api_secret) < 32:
                self.logger.error("❌ API凭证格式不正确")
                return False
            
            # 检查是否包含环境变量占位符
            if '${' in api_key or '${' in api_secret:
                self.logger.error("❌ API凭证包含未替换的环境变量")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ API凭证验证失败: {e}")
            return False
    
    def create_default_config(self, config_name: str, config_type: str) -> bool:
        """
        创建默认配置文件
        
        Args:
            config_name: 配置名称
            config_type: 配置类型
            
        Returns:
            是否创建成功
        """
        default_configs = {
            'trading': {
                'version': '2.0.0',
                'api': {
                    'exchange': 'binance',
                    'api_key': '${BINANCE_API_KEY}',
                    'api_secret': '${BINANCE_API_SECRET}',
                    'base_url': 'https://testnet.binance.vision',
                    'testnet': True
                },
                'trading': {
                    'symbols': ['BTCUSDT', 'ETHUSDT'],
                    'base_currency': 'USDT',
                    'position_size_ratio': 0.1,
                    'max_positions': 3
                },
                'risk_management': {
                    'max_daily_loss': 0.02,
                    'max_position_risk': 0.01,
                    'stop_loss': 0.02,
                    'take_profit': 0.04
                }
            },
            'production': {
                'version': '2.0.0',
                'api': {
                    'exchange': 'binance',
                    'api_key': '${BINANCE_API_KEY}',
                    'api_secret': '${BINANCE_API_SECRET}',
                    'base_url': 'https://api.binance.com',
                    'testnet': False
                },
                'trading': {
                    'symbols': ['BTCUSDT'],
                    'base_currency': 'USDT',
                    'position_size_ratio': 0.05,
                    'max_positions': 2
                },
                'risk_management': {
                    'max_daily_loss': 0.01,
                    'max_position_risk': 0.005,
                    'stop_loss': 0.015,
                    'take_profit': 0.03,
                    'max_consecutive_losses': 3
                },
                'monitoring': {
                    'log_level': 'INFO',
                    'alert_webhook': '${ALERT_WEBHOOK_URL:}',
                    'report_interval': 3600
                }
            }
        }
        
        if config_type not in default_configs:
            self.logger.error(f"❌ 不支持的配置类型: {config_type}")
            return False
        
        return self.save_config(config_name, default_configs[config_type])
    
    def reload_config(self, config_name: str) -> Dict[str, Any]:
        """
        重新加载配置（清除缓存）
        
        Args:
            config_name: 配置名称
            
        Returns:
            重新加载的配置
        """
        # 清除缓存
        self.configs.pop(config_name, None)
        
        # 重新加载
        return self.load_config(config_name)
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return {
            'config_dir': str(self.config_dir),
            'available_configs': self.list_configs(),
            'cached_configs': list(self.configs.keys()),
            'environment_variables': {
                key: '***' if 'key' in key.lower() or 'secret' in key.lower() or 'token' in key.lower() 
                else value
                for key, value in os.environ.items() 
                if key.startswith(('BINANCE_', 'OKX_', 'TRADING_', 'API_'))
            }
        }
    
    def __str__(self):
        return f"ConfigManager({self.config_dir}, configs={len(self.configs)})"
    
    def __repr__(self):
        return self.__str__()
