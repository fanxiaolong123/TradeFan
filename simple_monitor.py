#!/usr/bin/env python3
"""
TradeFan 简化监控面板
不依赖Docker的本地监控系统

运行方式:
python3 simple_monitor.py
然后访问: http://localhost:8080
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import threading
import time

# 简单的HTTP服务器
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from strategies.scalping_strategy import ScalpingStrategy
from strategies.trend_following_strategy import TrendFollowingStrategy, DEFAULT_TREND_CONFIG


class TradingMonitor:
    """交易监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.stats = {
            'start_time': datetime.now(),
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'current_positions': {},
            'recent_signals': [],
            'system_status': 'Running',
            'strategies': {
                'scalping': {'trades': 0, 'pnl': 0.0, 'win_rate': 0.0},
                'trend': {'trades': 0, 'pnl': 0.0, 'win_rate': 0.0}
            },
            'symbols': {
                'BTCUSDT': {'price': 45000, 'change_24h': 0.0, 'volume': 0},
                'ETHUSDT': {'price': 3000, 'change_24h': 0.0, 'volume': 0},
                'BNBUSDT': {'price': 300, 'change_24h': 0.0, 'volume': 0}
            }
        }
        
        # 初始化策略
        self.strategies = {}
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """初始化策略"""
        try:
            scalping_config = {
                'ema_fast': 8, 'ema_medium': 21, 'ema_slow': 55,
                'rsi_period': 14, 'signal_threshold': 0.6
            }
            self.strategies['scalping'] = ScalpingStrategy(**scalping_config)
            self.strategies['trend'] = TrendFollowingStrategy(DEFAULT_TREND_CONFIG)
            self.logger.info("✅ 策略初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 策略初始化失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        self.is_running = True
        self.logger.info("🚀 启动交易监控...")
        
        # 启动数据更新线程
        threading.Thread(target=self._update_data_loop, daemon=True).start()
        
        # 启动HTTP服务器
        if HTTP_AVAILABLE:
            self._start_web_server()
        else:
            self.logger.error("❌ HTTP服务器不可用")
    
    def _update_data_loop(self):
        """数据更新循环"""
        while self.is_running:
            try:
                self._update_mock_data()
                time.sleep(5)  # 每5秒更新一次
            except Exception as e:
                self.logger.error(f"数据更新错误: {e}")
                time.sleep(10)
    
    def _update_mock_data(self):
        """更新模拟数据"""
        import random
        
        # 更新价格数据
        for symbol in self.stats['symbols']:
            current_price = self.stats['symbols'][symbol]['price']
            # 添加±1%的价格波动
            change = random.uniform(-0.01, 0.01)
            new_price = current_price * (1 + change)
            
            self.stats['symbols'][symbol]['price'] = new_price
            self.stats['symbols'][symbol]['change_24h'] = change * 100
            self.stats['symbols'][symbol]['volume'] = random.randint(1000, 10000)
        
        # 模拟交易信号
        if random.random() < 0.3:  # 30%概率生成信号
            symbol = random.choice(list(self.stats['symbols'].keys()))
            strategy = random.choice(['scalping', 'trend'])
            signal = random.choice(['BUY', 'SELL', 'HOLD'])
            
            if signal in ['BUY', 'SELL']:
                # 添加到最近信号
                signal_data = {
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'strategy': strategy,
                    'symbol': symbol,
                    'signal': signal,
                    'price': self.stats['symbols'][symbol]['price']
                }
                
                self.stats['recent_signals'].insert(0, signal_data)
                if len(self.stats['recent_signals']) > 10:
                    self.stats['recent_signals'] = self.stats['recent_signals'][:10]
                
                # 更新交易统计
                self.stats['total_trades'] += 1
                self.stats['strategies'][strategy]['trades'] += 1
                
                # 模拟PnL
                pnl = random.uniform(-50, 100)
                self.stats['total_pnl'] += pnl
                self.stats['strategies'][strategy]['pnl'] += pnl
                
                if pnl > 0:
                    self.stats['successful_trades'] += 1
                
                # 更新胜率
                for strat in self.stats['strategies']:
                    if self.stats['strategies'][strat]['trades'] > 0:
                        win_count = max(1, int(self.stats['strategies'][strat]['trades'] * random.uniform(0.5, 0.8)))
                        self.stats['strategies'][strat]['win_rate'] = win_count / self.stats['strategies'][strat]['trades']
    
    def _start_web_server(self):
        """启动Web服务器"""
        try:
            server = HTTPServer(('localhost', 8080), MonitorRequestHandler)
            server.monitor = self  # 传递监控器实例
            
            self.logger.info("🌐 监控面板启动成功: http://localhost:8080")
            server.serve_forever()
            
        except Exception as e:
            self.logger.error(f"❌ Web服务器启动失败: {e}")
    
    def get_stats(self):
        """获取统计数据"""
        # 计算运行时间
        runtime = datetime.now() - self.stats['start_time']
        
        return {
            **self.stats,
            'runtime_seconds': int(runtime.total_seconds()),
            'runtime_formatted': str(runtime).split('.')[0],
            'win_rate': self.stats['successful_trades'] / max(1, self.stats['total_trades']),
            'timestamp': datetime.now().isoformat()
        }


class MonitorRequestHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        try:
            if self.path == '/':
                self._serve_dashboard()
            elif self.path == '/api/stats':
                self._serve_stats()
            elif self.path == '/api/health':
                self._serve_health()
            else:
                self._serve_404()
        except Exception as e:
            self._serve_error(str(e))
    
    def _serve_dashboard(self):
        """提供监控面板HTML"""
        html = self._generate_dashboard_html()
        self._send_response(200, html, 'text/html')
    
    def _serve_stats(self):
        """提供统计数据API"""
        stats = self.server.monitor.get_stats()
        self._send_response(200, json.dumps(stats, default=str), 'application/json')
    
    def _serve_health(self):
        """提供健康检查API"""
        health = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        self._send_response(200, json.dumps(health), 'application/json')
    
    def _serve_404(self):
        """404页面"""
        self._send_response(404, '<h1>404 Not Found</h1>', 'text/html')
    
    def _serve_error(self, error):
        """错误页面"""
        self._send_response(500, f'<h1>500 Server Error</h1><p>{error}</p>', 'text/html')
    
    def _send_response(self, code, content, content_type):
        """发送HTTP响应"""
        self.send_response(code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def _generate_dashboard_html(self):
        """生成监控面板HTML"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>TradeFan 交易监控面板</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #27ae60; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        .signals-table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .signals-table table { width: 100%; border-collapse: collapse; }
        .signals-table th, .signals-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        .signals-table th { background: #34495e; color: white; }
        .signal-buy { color: #27ae60; font-weight: bold; }
        .signal-sell { color: #e74c3c; font-weight: bold; }
        .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .status-running { color: #27ae60; }
        .price-up { color: #27ae60; }
        .price-down { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 TradeFan 交易监控面板</h1>
            <p>实时监控双策略交易系统 | <span id="status" class="status-running">系统运行中</span></p>
            <button class="refresh-btn" onclick="refreshData()">🔄 刷新数据</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="total-pnl">$0.00</div>
                <div class="stat-label">总盈亏 (PnL)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-trades">0</div>
                <div class="stat-label">总交易数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="win-rate">0%</div>
                <div class="stat-label">胜率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="runtime">00:00:00</div>
                <div class="stat-label">运行时间</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📈 短线策略</h3>
                <div>交易数: <span id="scalping-trades">0</span></div>
                <div>盈亏: <span id="scalping-pnl">$0.00</span></div>
                <div>胜率: <span id="scalping-winrate">0%</span></div>
            </div>
            <div class="stat-card">
                <h3>📊 趋势策略</h3>
                <div>交易数: <span id="trend-trades">0</span></div>
                <div>盈亏: <span id="trend-pnl">$0.00</span></div>
                <div>胜率: <span id="trend-winrate">0%</span></div>
            </div>
            <div class="stat-card">
                <h3>💰 价格监控</h3>
                <div>BTC: $<span id="btc-price">45000</span> (<span id="btc-change">0%</span>)</div>
                <div>ETH: $<span id="eth-price">3000</span> (<span id="eth-change">0%</span>)</div>
                <div>BNB: $<span id="bnb-price">300</span> (<span id="bnb-change">0%</span>)</div>
            </div>
        </div>
        
        <div class="signals-table">
            <h3 style="margin: 0; padding: 20px; background: #34495e; color: white;">📡 最近交易信号</h3>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>策略</th>
                        <th>交易对</th>
                        <th>信号</th>
                        <th>价格</th>
                    </tr>
                </thead>
                <tbody id="signals-tbody">
                    <tr><td colspan="5" style="text-align: center; color: #7f8c8d;">等待交易信号...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function refreshData() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDashboard(data) {
            // 更新主要统计
            document.getElementById('total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
            document.getElementById('total-trades').textContent = data.total_trades;
            document.getElementById('win-rate').textContent = (data.win_rate * 100).toFixed(1) + '%';
            document.getElementById('runtime').textContent = data.runtime_formatted;
            
            // 更新策略统计
            document.getElementById('scalping-trades').textContent = data.strategies.scalping.trades;
            document.getElementById('scalping-pnl').textContent = '$' + data.strategies.scalping.pnl.toFixed(2);
            document.getElementById('scalping-winrate').textContent = (data.strategies.scalping.win_rate * 100).toFixed(1) + '%';
            
            document.getElementById('trend-trades').textContent = data.strategies.trend.trades;
            document.getElementById('trend-pnl').textContent = '$' + data.strategies.trend.pnl.toFixed(2);
            document.getElementById('trend-winrate').textContent = (data.strategies.trend.win_rate * 100).toFixed(1) + '%';
            
            // 更新价格
            document.getElementById('btc-price').textContent = data.symbols.BTCUSDT.price.toFixed(2);
            document.getElementById('btc-change').textContent = data.symbols.BTCUSDT.change_24h.toFixed(2) + '%';
            document.getElementById('btc-change').className = data.symbols.BTCUSDT.change_24h >= 0 ? 'price-up' : 'price-down';
            
            document.getElementById('eth-price').textContent = data.symbols.ETHUSDT.price.toFixed(2);
            document.getElementById('eth-change').textContent = data.symbols.ETHUSDT.change_24h.toFixed(2) + '%';
            document.getElementById('eth-change').className = data.symbols.ETHUSDT.change_24h >= 0 ? 'price-up' : 'price-down';
            
            document.getElementById('bnb-price').textContent = data.symbols.BNBUSDT.price.toFixed(2);
            document.getElementById('bnb-change').textContent = data.symbols.BNBUSDT.change_24h.toFixed(2) + '%';
            document.getElementById('bnb-change').className = data.symbols.BNBUSDT.change_24h >= 0 ? 'price-up' : 'price-down';
            
            // 更新信号表
            const tbody = document.getElementById('signals-tbody');
            if (data.recent_signals.length > 0) {
                tbody.innerHTML = data.recent_signals.map(signal => 
                    `<tr>
                        <td>${signal.time}</td>
                        <td>${signal.strategy}</td>
                        <td>${signal.symbol}</td>
                        <td class="signal-${signal.signal.toLowerCase()}">${signal.signal}</td>
                        <td>$${signal.price.toFixed(2)}</td>
                    </tr>`
                ).join('');
            }
        }
        
        // 自动刷新
        setInterval(refreshData, 5000);
        
        // 初始加载
        refreshData();
    </script>
</body>
</html>
        '''
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass


def main():
    """主函数"""
    print("🚀 TradeFan 简化监控系统")
    print("=" * 40)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if not HTTP_AVAILABLE:
        print("❌ HTTP服务器不可用，请安装Python标准库")
        return 1
    
    try:
        # 创建监控器
        monitor = TradingMonitor()
        
        print("🌐 启动监控面板...")
        print("📊 访问地址: http://localhost:8080")
        print("💡 按 Ctrl+C 停止监控")
        print()
        
        # 启动监控
        monitor.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n⚠️ 监控被用户中断")
        return 0
    except Exception as e:
        print(f"\n❌ 监控启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
