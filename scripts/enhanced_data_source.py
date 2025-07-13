#!/usr/bin/env python3
"""
增强数据源脚本 - 添加更多时间框架和币种
支持5分钟、15分钟、30分钟数据，以及DOGE、PEPE、AAVE等币种
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
        
        batch_count = 0
        max_batches = 50  # 限制批次数量，避免过长时间
        
        while current_time < end_time and batch_count < max_batches:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_time,
                'limit': limit
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if not data or isinstance(data, dict):
                    if isinstance(data, dict) and 'code' in data:
                        print(f"   ⚠️  API错误: {data.get('msg', 'Unknown error')}")
                    break
                    
                all_data.extend(data)
                
                # 更新时间戳到最后一条数据的时间
                current_time = data[-1][6] + 1  # close_time + 1ms
                batch_count += 1
                
                if batch_count % 5 == 0:  # 每5批显示一次进度
                    print(f"   已获取 {len(all_data)} 条数据...")
                
                time.sleep(0.1)  # 避免请求过快
                
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")
                break
    else:
        # 获取最近的数据
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            all_data = response.json()
        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return None
    
    if not all_data:
        print("   ❌ 未获取到数据")
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
    
    print(f"   ✅ 成功获取 {len(result)} 条数据")
    print(f"   📅 时间范围: {result['datetime'].min()} 到 {result['datetime'].max()}")
    
    return result

def save_data(data, filename):
    """保存数据到文件"""
    os.makedirs('data/historical', exist_ok=True)
    
    # 保存为多种格式
    csv_path = f'data/historical/{filename}.csv'
    parquet_path = f'data/historical/{filename}.parquet'
    
    data.to_csv(csv_path, index=False)
    data.to_parquet(parquet_path, index=False)
    
    print(f"   💾 数据已保存: {filename}")

def main():
    """主函数 - 获取增强的历史数据"""
    print("🚀 TradeFan 增强数据源获取工具")
    print("支持更多时间框架和币种")
    print("=" * 60)
    
    # 扩展的交易对列表
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT',  # 原有币种
        'DOGEUSDT', 'PEPEUSDT', 'AAVEUSDT'  # 新增币种
    ]
    
    # 扩展的时间框架列表
    timeframes = [
        '5m', '15m', '30m',  # 新增短时间框架
        '1h', '4h', '1d'     # 原有时间框架
    ]
    
    print(f"📊 计划获取数据:")
    print(f"   币种: {len(symbols)} 个 - {', '.join([s.replace('USDT', '') for s in symbols])}")
    print(f"   时间框架: {len(timeframes)} 个 - {', '.join(timeframes)}")
    print(f"   总配置: {len(symbols) * len(timeframes)} 个")
    
    # 根据时间框架设置不同的历史数据范围
    timeframe_config = {
        '5m': {'days': 30, 'desc': '30天'},    # 5分钟数据量大，只取30天
        '15m': {'days': 90, 'desc': '90天'},   # 15分钟数据，取90天
        '30m': {'days': 180, 'desc': '180天'}, # 30分钟数据，取180天
        '1h': {'days': 365, 'desc': '365天'},   # 1小时数据，取1年
        '4h': {'days': 730, 'desc': '730天'},   # 4小时数据，取2年
        '1d': {'days': 730, 'desc': '730天'}    # 日线数据，取2年
    }
    
    success_count = 0
    total_records = 0
    
    for symbol in symbols:
        print(f"\n🔍 处理币种: {symbol}")
        print("-" * 40)
        
        for timeframe in timeframes:
            try:
                # 计算开始日期
                days_back = timeframe_config[timeframe]['days']
                start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
                
                print(f"   📈 {timeframe} ({timeframe_config[timeframe]['desc']})")
                
                # 获取数据
                data = get_binance_data(
                    symbol=symbol, 
                    interval=timeframe, 
                    start_date=start_date
                )
                
                if data is not None and len(data) > 50:  # 至少50条数据才保存
                    filename = f"{symbol}_{timeframe}_binance"
                    save_data(data, filename)
                    success_count += 1
                    total_records += len(data)
                    print(f"   ✅ 成功: {len(data)} 条数据")
                else:
                    print(f"   ⚠️  数据不足: {len(data) if data is not None else 0} 条")
                    
            except Exception as e:
                print(f"   ❌ 失败: {str(e)}")
            
            # 短暂延迟，避免API限制
            time.sleep(0.2)
    
    # 汇总报告
    print(f"\n" + "=" * 60)
    print(f"📊 数据获取完成汇总:")
    print(f"   成功配置: {success_count}/{len(symbols) * len(timeframes)}")
    print(f"   总数据量: {total_records:,} 条记录")
    print(f"   成功率: {success_count/(len(symbols) * len(timeframes))*100:.1f}%")
    
    # 验证数据文件
    print(f"\n🔍 验证数据文件:")
    data_dir = 'data/historical'
    if os.path.exists(data_dir):
        files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        print(f"   CSV文件: {len(files)} 个")
        
        # 按币种分组显示
        symbol_files = {}
        for file in files:
            if '_binance.csv' in file:
                parts = file.split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    timeframe = parts[1]
                    if symbol not in symbol_files:
                        symbol_files[symbol] = []
                    symbol_files[symbol].append(timeframe)
        
        for symbol, tfs in symbol_files.items():
            print(f"   {symbol}: {', '.join(sorted(tfs))}")
    
    print(f"\n💡 使用建议:")
    print(f"   1. 短线策略: 使用5m, 15m数据")
    print(f"   2. 中线策略: 使用30m, 1h数据") 
    print(f"   3. 长线策略: 使用4h, 1d数据")
    print(f"   4. 多时间框架: 结合不同周期确认信号")
    
    print(f"\n🎉 数据获取完成!")

if __name__ == "__main__":
    main()
