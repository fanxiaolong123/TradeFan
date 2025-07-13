"""
增强数据模块 - 使用完整的历史数据
解决30条数据限制问题，支持本地数据和实时数据
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import glob

class EnhancedDataModule:
    """增强数据模块 - 支持完整历史数据"""
    
    def __init__(self):
        # 简化日志初始化
        import logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.historical_data_dir = "data/historical"
        self.cache = {}
        
        # 检查数据目录
        if not os.path.exists(self.historical_data_dir):
            self.logger.warning(f"历史数据目录不存在: {self.historical_data_dir}")
            os.makedirs(self.historical_data_dir, exist_ok=True)
    
    def get_historical_data(self, symbol: str, timeframe: str = '1d', 
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取历史数据 - 优先使用本地完整数据
        
        Args:
            symbol: 交易对 (BTC/USDT, ETH/USDT等)
            timeframe: 时间框架 (1d, 4h, 1h等)
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            # 转换符号格式
            binance_symbol = self._convert_to_binance_symbol(symbol)
            
            # 构建文件名
            filename = f"{binance_symbol}_{timeframe}_binance.parquet"
            file_path = os.path.join(self.historical_data_dir, filename)
            
            # 检查本地文件
            if os.path.exists(file_path):
                self.logger.info(f"使用本地数据: {filename}")
                data = pd.read_parquet(file_path)
                
                # 确保datetime列是datetime类型
                if 'datetime' in data.columns:
                    data['datetime'] = pd.to_datetime(data['datetime'])
                
                # 过滤日期范围
                if start_date:
                    data = data[data['datetime'] >= pd.to_datetime(start_date)]
                if end_date:
                    data = data[data['datetime'] <= pd.to_datetime(end_date)]
                
                self.logger.info(f"✅ 本地数据加载成功: {len(data)} 条记录")
                self.logger.info(f"   时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
                
                return data
            
            # 如果本地文件不存在，尝试CSV格式
            csv_filename = f"{binance_symbol}_{timeframe}_binance.csv"
            csv_file_path = os.path.join(self.historical_data_dir, csv_filename)
            
            if os.path.exists(csv_file_path):
                self.logger.info(f"使用本地CSV数据: {csv_filename}")
                data = pd.read_csv(csv_file_path)
                data['datetime'] = pd.to_datetime(data['datetime'])
                
                # 过滤日期范围
                if start_date:
                    data = data[data['datetime'] >= pd.to_datetime(start_date)]
                if end_date:
                    data = data[data['datetime'] <= pd.to_datetime(end_date)]
                
                self.logger.info(f"✅ 本地CSV数据加载成功: {len(data)} 条记录")
                return data
            
            # 如果本地数据不存在，生成警告并返回模拟数据
            self.logger.warning(f"本地数据文件不存在: {filename}")
            self.logger.warning("请运行 python3 scripts/fix_data_source.py 获取完整数据")
            
            return self._generate_fallback_data(symbol, timeframe, start_date, end_date)
            
        except Exception as e:
            self.logger.error(f"数据加载失败 {symbol}: {str(e)}")
            return self._generate_fallback_data(symbol, timeframe, start_date, end_date)
    
    def _convert_to_binance_symbol(self, symbol: str) -> str:
        """转换为Binance符号格式"""
        # 移除分隔符
        return symbol.replace('/', '').replace('-', '')
    
    def _generate_fallback_data(self, symbol: str, timeframe: str = '1d',
                               start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """生成备用模拟数据"""
        self.logger.warning(f"使用模拟数据: {symbol}")
        
        # 设置默认日期范围
        if not start_date:
            start_date = '2024-01-01'
        if not end_date:
            end_date = '2024-12-31'
        
        # 根据时间框架生成日期范围
        freq_map = {
            '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '1H', '4h': '4H', '1d': '1D'
        }
        
        freq = freq_map.get(timeframe, '1D')
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        # 模拟价格数据
        np.random.seed(42)
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 500
        
        prices = []
        current_price = base_price
        
        for _ in range(len(dates)):
            # 随机游走
            change = np.random.normal(0, 0.02)  # 2%标准差
            current_price *= (1 + change)
            prices.append(current_price)
        
        # 生成OHLCV数据
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            high = close * (1 + abs(np.random.normal(0, 0.01)))
            low = close * (1 - abs(np.random.normal(0, 0.01)))
            open_price = prices[i-1] if i > 0 else close
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                'datetime': date,
                'open': open_price,
                'high': max(open_price, high, close),
                'low': min(open_price, low, close),
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        self.logger.info(f"生成模拟数据: {len(df)} 条记录")
        
        return df
    
    def get_available_data_files(self) -> List[str]:
        """获取可用的数据文件列表"""
        if not os.path.exists(self.historical_data_dir):
            return []
        
        files = []
        for ext in ['*.parquet', '*.csv']:
            pattern = os.path.join(self.historical_data_dir, ext)
            files.extend(glob.glob(pattern))
        
        return [os.path.basename(f) for f in files]
    
    def get_data_summary(self) -> Dict:
        """获取数据摘要信息"""
        summary = {
            'total_files': 0,
            'symbols': set(),
            'timeframes': set(),
            'date_ranges': {}
        }
        
        files = self.get_available_data_files()
        summary['total_files'] = len(files)
        
        for file in files:
            if '_binance.' in file:
                parts = file.split('_')
                if len(parts) >= 3:
                    symbol = parts[0]
                    timeframe = parts[1]
                    
                    summary['symbols'].add(symbol)
                    summary['timeframes'].add(timeframe)
                    
                    # 尝试读取文件获取日期范围
                    try:
                        file_path = os.path.join(self.historical_data_dir, file)
                        if file.endswith('.parquet'):
                            df = pd.read_parquet(file_path)
                        else:
                            df = pd.read_csv(file_path)
                        
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        date_range = f"{df['datetime'].min()} 到 {df['datetime'].max()}"
                        summary['date_ranges'][f"{symbol}_{timeframe}"] = {
                            'range': date_range,
                            'count': len(df)
                        }
                    except:
                        pass
        
        summary['symbols'] = list(summary['symbols'])
        summary['timeframes'] = list(summary['timeframes'])
        
        return summary
    
    def validate_data_quality(self, symbol: str, timeframe: str = '1d') -> Dict:
        """验证数据质量"""
        try:
            data = self.get_historical_data(symbol, timeframe)
            
            if data.empty:
                return {'status': 'error', 'message': '数据为空'}
            
            # 检查数据完整性
            required_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                return {
                    'status': 'error', 
                    'message': f'缺少列: {missing_columns}'
                }
            
            # 检查数据质量
            quality_issues = []
            
            # 检查空值
            null_counts = data.isnull().sum()
            if null_counts.sum() > 0:
                quality_issues.append(f"空值: {null_counts.to_dict()}")
            
            # 检查价格逻辑
            invalid_prices = data[(data['high'] < data['low']) | 
                                (data['high'] < data['open']) | 
                                (data['high'] < data['close']) |
                                (data['low'] > data['open']) | 
                                (data['low'] > data['close'])]
            
            if len(invalid_prices) > 0:
                quality_issues.append(f"价格逻辑错误: {len(invalid_prices)} 条")
            
            # 检查重复时间
            duplicate_times = data['datetime'].duplicated().sum()
            if duplicate_times > 0:
                quality_issues.append(f"重复时间: {duplicate_times} 条")
            
            return {
                'status': 'success',
                'total_records': len(data),
                'date_range': f"{data['datetime'].min()} 到 {data['datetime'].max()}",
                'quality_issues': quality_issues if quality_issues else ['无问题'],
                'price_range': f"${data['close'].min():.2f} - ${data['close'].max():.2f}"
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


def test_enhanced_data_module():
    """测试增强数据模块"""
    print("🔍 测试增强数据模块...")
    
    data_module = EnhancedDataModule()
    
    # 1. 检查可用数据文件
    print("\n📁 可用数据文件:")
    files = data_module.get_available_data_files()
    for file in files[:10]:  # 只显示前10个
        print(f"   📄 {file}")
    
    if len(files) > 10:
        print(f"   ... 还有 {len(files) - 10} 个文件")
    
    # 2. 获取数据摘要
    print("\n📊 数据摘要:")
    summary = data_module.get_data_summary()
    print(f"   总文件数: {summary['total_files']}")
    print(f"   可用币种: {summary['symbols']}")
    print(f"   时间框架: {summary['timeframes']}")
    
    # 3. 测试数据加载
    print("\n🧪 测试数据加载:")
    test_cases = [
        ('BTC/USDT', '1d'),
        ('ETH/USDT', '4h'),
        ('BNB/USDT', '1h')
    ]
    
    for symbol, timeframe in test_cases:
        print(f"\n   测试 {symbol} {timeframe}:")
        
        # 加载数据
        data = data_module.get_historical_data(symbol, timeframe)
        print(f"   ✅ 数据条数: {len(data)}")
        
        if len(data) > 0:
            print(f"   📅 时间范围: {data['datetime'].min()} 到 {data['datetime'].max()}")
            print(f"   💰 价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
        
        # 验证数据质量
        quality = data_module.validate_data_quality(symbol, timeframe)
        print(f"   🔍 数据质量: {quality['status']}")
        if quality['status'] == 'success':
            print(f"   📊 质量问题: {quality['quality_issues']}")
    
    print("\n🎉 增强数据模块测试完成!")


if __name__ == "__main__":
    test_enhanced_data_module()
