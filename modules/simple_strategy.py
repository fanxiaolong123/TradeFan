"""
简化策略模块 - 不依赖TA-Lib
用于系统测试和基础功能验证
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

class SimpleMovingAverageStrategy:
    """简单移动平均策略"""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = "SimpleMA"
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # 计算简单移动平均线
        df['sma_fast'] = df['close'].rolling(window=self.fast_period).mean()
        df['sma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        
        # 计算RSI（简化版本）
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        
        # 生成买入信号
        buy_condition = (
            (df['sma_fast'] > df['sma_slow']) &  # 快线在慢线上方
            (df['sma_fast'].shift(1) <= df['sma_slow'].shift(1)) &  # 前一期快线在慢线下方（金叉）
            (df['rsi'] < 70)  # RSI不超买
        )
        
        # 生成卖出信号
        sell_condition = (
            (df['sma_fast'] < df['sma_slow']) &  # 快线在慢线下方
            (df['sma_fast'].shift(1) >= df['sma_slow'].shift(1)) &  # 前一期快线在慢线上方（死叉）
            (df['rsi'] > 30)  # RSI不超卖
        )
        
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # 计算持仓状态
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
        
        return df
    
    def get_strategy_info(self) -> Dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'description': '简单移动平均线交叉策略'
        }

class SimpleTrendStrategy:
    """简单趋势策略"""
    
    def __init__(self, ma_period: int = 20, volatility_period: int = 20):
        self.ma_period = ma_period
        self.volatility_period = volatility_period
        self.name = "SimpleTrend"
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        df = data.copy()
        
        # 移动平均线
        df['ma'] = df['close'].rolling(window=self.ma_period).mean()
        
        # 价格相对于均线的位置
        df['price_vs_ma'] = (df['close'] - df['ma']) / df['ma']
        
        # 波动率（标准差）
        df['volatility'] = df['close'].pct_change().rolling(window=self.volatility_period).std()
        
        # 趋势强度（价格变化率）
        df['trend_strength'] = df['close'].pct_change(self.ma_period)
        
        return df
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = self.calculate_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        
        # 买入条件：价格突破均线向上，且趋势强度足够
        buy_condition = (
            (df['close'] > df['ma']) &  # 价格在均线上方
            (df['close'].shift(1) <= df['ma'].shift(1)) &  # 前一期价格在均线下方
            (df['trend_strength'] > 0.02) &  # 趋势强度大于2%
            (df['volatility'] < df['volatility'].rolling(50).quantile(0.8))  # 波动率不太高
        )
        
        # 卖出条件：价格跌破均线向下
        sell_condition = (
            (df['close'] < df['ma']) &  # 价格在均线下方
            (df['close'].shift(1) >= df['ma'].shift(1)) &  # 前一期价格在均线上方
            (df['trend_strength'] < -0.02)  # 下跌趋势强度大于2%
        )
        
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # 计算持仓状态
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
        
        return df
    
    def get_strategy_info(self) -> Dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'ma_period': self.ma_period,
            'volatility_period': self.volatility_period,
            'description': '简单趋势突破策略'
        }

def get_available_strategies() -> Dict:
    """获取可用策略列表"""
    return {
        'SimpleMA': SimpleMovingAverageStrategy,
        'SimpleTrend': SimpleTrendStrategy
    }

if __name__ == "__main__":
    # 测试策略
    import matplotlib.pyplot as plt
    
    # 生成测试数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=200, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    
    test_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + np.abs(np.random.randn(200) * 0.3),
        'low': prices - np.abs(np.random.randn(200) * 0.3),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 200)
    })
    
    # 测试简单移动平均策略
    strategy = SimpleMovingAverageStrategy(fast_period=10, slow_period=20)
    result = strategy.generate_signals(test_data)
    
    print("策略测试完成")
    print(f"总信号数: {result['signal'].abs().sum()}")
    print(f"买入信号: {(result['signal'] == 1).sum()}")
    print(f"卖出信号: {(result['signal'] == -1).sum()}")
    
    # 绘制结果
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(result.index, result['close'], label='Price', alpha=0.7)
    plt.plot(result.index, result['sma_fast'], label=f'SMA{strategy.fast_period}', alpha=0.8)
    plt.plot(result.index, result['sma_slow'], label=f'SMA{strategy.slow_period}', alpha=0.8)
    
    # 标记买卖点
    buy_points = result[result['signal'] == 1]
    sell_points = result[result['signal'] == -1]
    
    plt.scatter(buy_points.index, buy_points['close'], color='green', marker='^', s=100, label='Buy')
    plt.scatter(sell_points.index, sell_points['close'], color='red', marker='v', s=100, label='Sell')
    
    plt.title('Simple Moving Average Strategy')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.subplot(2, 1, 2)
    plt.plot(result.index, result['rsi'], label='RSI')
    plt.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought')
    plt.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold')
    plt.title('RSI Indicator')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/Users/fanxiaolong/Fan/TradeFan/results/strategy_test.png', dpi=300, bbox_inches='tight')
    print("图表已保存到 results/strategy_test.png")
