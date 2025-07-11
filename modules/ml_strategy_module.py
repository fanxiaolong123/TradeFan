"""
机器学习策略模块
使用机器学习模型进行交易信号预测
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import joblib
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from .strategy_module import BaseStrategy
from .log_module import LogModule

class MLFeatureEngineer:
    """机器学习特征工程"""
    
    def __init__(self, logger=None):
        self.logger = logger or LogModule()
        self.feature_names = []
    
    def create_basic_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """创建基础特征"""
        df = data.copy()
        
        try:
            # 价格特征
            df['returns'] = df['close'].pct_change()
            df['price_change'] = (df['close'] - df['open']) / df['open']
            df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
            
            # 简单移动平均线
            for period in [5, 10, 20]:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
                df[f'price_to_sma_{period}'] = df['close'] / df[f'sma_{period}'] - 1
            
            # 成交量特征
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # 波动率
            df['volatility'] = df['returns'].rolling(window=20).std()
            
            # 滞后特征
            for lag in [1, 2, 3]:
                df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
            
            # 删除无限值和NaN
            df = df.replace([np.inf, -np.inf], np.nan)
            
            self.logger.info(f"创建了基础特征")
            
        except Exception as e:
            self.logger.error(f"特征工程失败: {e}")
        
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备机器学习特征"""
        # 创建特征
        df = self.create_basic_features(data)
        
        # 选择数值特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 排除原始OHLCV列
        exclude_cols = ['open', 'high', 'low', 'close', 'volume']
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        # 特征数据
        X = df[feature_cols].copy()
        
        # 删除包含NaN的行
        X = X.dropna()
        
        self.feature_names = X.columns.tolist()
        self.logger.info(f"准备了{len(X)}行数据，{len(X.columns)}个特征")
        
        return X

class SimpleMLStrategy(BaseStrategy):
    """简化的机器学习策略"""
    
    def __init__(self, params: Dict, logger=None):
        super().__init__(params, logger)
        
        self.model = None
        self.feature_engineer = MLFeatureEngineer(logger)
        self.signal_threshold = params.get('signal_threshold', 0.6)
        
        if self.logger:
            self.logger.info("初始化简化ML策略")
    
    def create_labels(self, data: pd.DataFrame) -> pd.Series:
        """创建训练标签"""
        # 计算未来1期收益率
        future_returns = data['close'].pct_change().shift(-1)
        
        # 创建分类标签: 1买入, 0持有, -1卖出
        labels = pd.Series(0, index=data.index)
        labels[future_returns > 0.005] = 1  # 上涨0.5%以上买入
        labels[future_returns < -0.005] = -1  # 下跌0.5%以上卖出
        
        return labels
    
    def train_model(self, data: pd.DataFrame) -> Dict[str, Any]:
        """训练简化模型"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            
            self.logger.info("开始训练ML模型...")
            
            # 准备特征和标签
            X = self.feature_engineer.prepare_features(data)
            y = self.create_labels(data)
            
            # 对齐数据
            common_index = X.index.intersection(y.index)
            X = X.loc[common_index]
            y = y.loc[common_index]
            
            if len(X) < 50:
                self.logger.error("训练数据不足")
                return {}
            
            # 标准化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 分割数据
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.3, random_state=42
            )
            
            # 训练模型
            self.model = RandomForestClassifier(n_estimators=50, random_state=42)
            self.model.fit(X_train, y_train)
            
            # 评估
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)
            
            self.logger.info(f"模型训练完成: 训练准确率{train_score:.3f}, 测试准确率{test_score:.3f}")
            
            return {
                'train_score': train_score,
                'test_score': test_score,
                'model_trained': True
            }
            
        except ImportError:
            self.logger.warning("scikit-learn未安装，无法使用ML策略")
            return {}
        except Exception as e:
            self.logger.error(f"模型训练失败: {e}")
            return {}
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """计算指标（兼容基类）"""
        return {}
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        signals = pd.Series(0, index=data.index)
        
        if self.model is None:
            # 如果没有训练模型，使用简单规则
            returns = data['close'].pct_change()
            sma_5 = data['close'].rolling(5).mean()
            sma_20 = data['close'].rolling(20).mean()
            
            # 简单的均线策略作为fallback
            buy_condition = (data['close'] > sma_5) & (sma_5 > sma_20)
            sell_condition = (data['close'] < sma_5) & (sma_5 < sma_20)
            
            signals[buy_condition] = 1
            signals[sell_condition] = -1
            
            return signals
        
        try:
            # 使用ML模型预测
            X = self.feature_engineer.prepare_features(data)
            
            if len(X) == 0:
                return signals
            
            # 预测
            predictions = self.model.predict(X)
            
            # 转换为信号
            for idx, pred in zip(X.index, predictions):
                if idx in signals.index:
                    signals.loc[idx] = pred
            
        except Exception as e:
            self.logger.error(f"ML信号生成失败: {e}")
        
        return signals
