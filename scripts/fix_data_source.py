#!/usr/bin/env python3
"""
数据源修复脚本 - 获取完整的历史数据
支持多个免费数据源，解决30条数据限制问题
"""

import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import os
import sys

def get_binance_data(symbol='BTCUSDT', interval='1d', limit=1000, start_date=None):
    """
    从Binance获取完整历史数据 (免费，无限制)
    
    Args:
        symbol: 交易对 (BTCUSDT, ETHUSDT等)
        interval: 时间间隔 (1m, 5m, 15m, 30m, 1h, 4h, 1d等)
        limit: 数据条数 (最大1000)
        start_date: 开始日期 ('2023-01-01')
    """
    print(f"📊 获取 {symbol} 数据 (间隔: {interval})...")
    
    url = "https://api.binance.com/api/v3/klines"
    
    all_data = []
    
    # 如果指定了开始日期，分批获取
    if start_date:
        start_time = int(pd.to_datetime(start_date).timestamp() * 1000)
        current_time = start_time
        end_time = int(datetime.now().timestamp() * 1000)
        
        while current_time < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_time,
                'limit': limit
            }
            
            try:
                response = requests.get(url, params=params)
                data = response.json()
                
                if not data:
                    break
                    
                all_data.extend(data)
                
                # 更新时间戳到最后一条数据的时间
                current_time = data[-1][6] + 1  # close_time + 1ms
                
                print(f"   已获取 {len(all_data)} 条数据...")
                time.sleep(0.1)  # 避免请求过快
                
            except Exception as e:
                print(f"❌ 请求失败: {e}")
                break
    else:
        # 获取最近的数据
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = requests.get(url, params=params)
        all_data = response.json()
    
    if not all_data:
        print("❌ 未获取到数据")
        return None
    
    # 转换为DataFrame
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # 数据类型转换
    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    # 选择需要的列
    result = df[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
    result = result.sort_values('datetime').reset_index(drop=True)
    
    print(f"✅ 成功获取 {len(result)} 条数据")
    print(f"   时间范围: {result['datetime'].min()} 到 {result['datetime'].max()}")
    
    return result

def get_yahoo_finance_data(symbol='BTC-USD', period='2y', interval='1d'):
    """
    使用yfinance获取Yahoo Finance数据
    """
    try:
        import yfinance as yf
        
        print(f"📊 从Yahoo Finance获取 {symbol} 数据...")
        
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            print("❌ Yahoo Finance返回空数据")
            return None
        
        # 重置索引并标准化列名
        data.reset_index(inplace=True)
        data = data.rename(columns={
            'Date': 'datetime',
            'Open': 'open', 
            'High': 'high', 
            'Low': 'low', 
            'Close': 'close', 
            'Volume': 'volume'
        })
        
        result = data[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        print(f"✅ 成功获取 {len(result)} 条数据")
        print(f"   时间范围: {result['datetime'].min()} 到 {result['datetime'].max()}")
        
        return result
        
    except ImportError:
        print("❌ yfinance未安装，请运行: pip install yfinance")
        return None
    except Exception as e:
        print(f"❌ Yahoo Finance获取失败: {e}")
        return None

def save_data(data, filename):
    """保存数据到文件"""
    os.makedirs('data/historical', exist_ok=True)
    
    # 保存为多种格式
    csv_path = f'data/historical/{filename}.csv'
    parquet_path = f'data/historical/{filename}.parquet'
    
    data.to_csv(csv_path, index=False)
    data.to_parquet(parquet_path, index=False)
    
    print(f"💾 数据已保存:")
    print(f"   CSV: {csv_path}")
    print(f"   Parquet: {parquet_path}")

def main():
    """主函数 - 获取完整历史数据"""
    print("🚀 TradeFan 数据源修复工具")
    print("=" * 50)
    
    # 1. 获取Binance数据 (推荐)
    print("\n📊 方案1: Binance API (免费，数据最全)")
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['1d', '4h', '1h']
    
    for symbol in symbols:
        for interval in intervals:
            try:
                # 获取过去2年的数据
                start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
                data = get_binance_data(symbol, interval, start_date=start_date)
                
                if data is not None and len(data) > 100:
                    filename = f"{symbol}_{interval}_binance"
                    save_data(data, filename)
                    print(f"✅ {symbol} {interval} 数据获取完成: {len(data)} 条\n")
                else:
                    print(f"⚠️  {symbol} {interval} 数据不足\n")
                    
            except Exception as e:
                print(f"❌ {symbol} {interval} 获取失败: {e}\n")
    
    # 2. 获取Yahoo Finance数据 (备用)
    print("\n📊 方案2: Yahoo Finance (备用)")
    
    yahoo_symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD']
    
    for symbol in yahoo_symbols:
        try:
            data = get_yahoo_finance_data(symbol, period='2y', interval='1d')
            
            if data is not None and len(data) > 100:
                filename = f"{symbol.replace('-', '')}_1d_yahoo"
                save_data(data, filename)
                print(f"✅ {symbol} 数据获取完成: {len(data)} 条\n")
            else:
                print(f"⚠️  {symbol} 数据不足\n")
                
        except Exception as e:
            print(f"❌ {symbol} 获取失败: {e}\n")
    
    # 3. 数据验证
    print("\n🔍 数据验证:")
    data_dir = 'data/historical'
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        print(f"✅ 已保存 {len(files)} 个数据文件:")
        
        for file in sorted(files):
            file_path = os.path.join(data_dir, file)
            try:
                df = pd.read_csv(file_path)
                print(f"   📁 {file}: {len(df)} 条记录")
            except:
                print(f"   ❌ {file}: 读取失败")
    
    print("\n🎉 数据源修复完成!")
    print("\n💡 使用建议:")
    print("1. Binance数据质量最好，推荐用于回测")
    print("2. 数据已保存到 data/historical/ 目录")
    print("3. 可以修改 data_module.py 使用本地数据")

if __name__ == "__main__":
    main()
