#!/usr/bin/env python3
"""
TradeFan 生产环境Web监控面板
实时监控真实交易数据
"""

import os
import sys
import json
import time
import requests
import hmac
import hashlib
import threading
import yaml
from datetime import datetime, timedelta
from urllib.parse import urlencode
from http.server import HTTPServer, BaseHTTPRequestHandler

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ProductionWebMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.api_key = self.config['api']['api_key']
        self.api_secret = self.config['api']['api_secret']
        self.base_url = self.config['api']['base_url']
        
        # 缓存数据
        self.cached_data = {
            'account_info': {},
            'open_orders': [],
            'recent_trades': {},
            'market_prices': {},
            'system_status': 'Unknown',
            'last_update': None
        }
        
        self.is_running = False
        
    def load_config(self):
        """加载生产配置"""
        config_path = "config/live_production_config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            return {'api': {'api_key': '', 'api_secret': '', 'base_url': 'https://api.binance.com'}}
    
    def create_signature(self, params: dict) -> str:
        """创建API签名"""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def make_request(self, endpoint: str, params: dict = None) -> dict:
        """发送API请求"""
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self.create_signature(params)
        
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {}
        except Exception as e:
            return {}
    
    def update_data(self):
        """更新所有数据"""
        try:
            # 账户信息
            self.cached_data['account_info'] = self.make_request("/api/v3/account")
            
            # 当前挂单
            self.cached_data['open_orders'] = self.make_request("/api/v3/openOrders")
            
            # 最近交易
            symbols = ['BTCUSDT', 'ETHUSDT']
            for symbol in symbols:
                trades = self.make_request("/api/v3/myTrades", {"symbol": symbol, "limit": 10})
                self.cached_data['recent_trades'][symbol] = trades
            
            # 市场价格
            for symbol in symbols:
                try:
                    url = f"{self.base_url}/api/v3/ticker/24hr"
                    response = requests.get(url, params={"symbol": symbol}, timeout=10)
                    if response.status_code == 200:
                        self.cached_data['market_prices'][symbol] = response.json()
                except:
                    pass
            
            # 系统状态
            import subprocess
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                if 'start_live_trading.py' in result.stdout:
                    self.cached_data['system_status'] = 'Running'
                else:
                    self.cached_data['system_status'] = 'Stopped'
            except:
                self.cached_data['system_status'] = 'Unknown'
            
            self.cached_data['last_update'] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"数据更新错误: {e}")
    
    def start_data_updater(self):
        """启动数据更新线程"""
        def update_loop():
            while self.is_running:
                self.update_data()
                time.sleep(30)  # 每30秒更新一次
        
        threading.Thread(target=update_loop, daemon=True).start()
    
    def start_web_server(self):
        """启动Web服务器"""
        self.is_running = True
        self.start_data_updater()
        
        try:
            server = HTTPServer(('localhost', 8081), ProductionRequestHandler)
            server.monitor = self
            
            print("🌐 生产环境监控面板启动成功: http://localhost:8081")
            server.serve_forever()
            
        except Exception as e:
            print(f"❌ Web服务器启动失败: {e}")


class ProductionRequestHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        try:
            if self.path == '/':
                self._serve_dashboard()
            elif self.path == '/api/production-stats':
                self._serve_production_stats()
            elif self.path == '/api/health':
                self._serve_health()
            else:
                self._serve_404()
        except Exception as e:
            self._serve_error(str(e))
    
    def _serve_dashboard(self):
        """提供监控面板HTML"""
        html = self._generate_production_dashboard_html()
        self._send_response(200, html, 'text/html')
    
    def _serve_production_stats(self):
        """提供生产统计数据API"""
        stats = self._format_production_stats()
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
    
    def _format_production_stats(self):
        """格式化生产统计数据"""
        data = self.server.monitor.cached_data
        
        # 处理账户信息
        account = data.get('account_info', {})
        balances = {}
        total_value_usdt = 0
        
        if account and 'balances' in account:
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
                    
                    if asset == 'USDT':
                        total_value_usdt += total
                    elif asset == 'BTC' and 'BTCUSDT' in data.get('market_prices', {}):
                        btc_price = float(data['market_prices']['BTCUSDT'].get('lastPrice', 0))
                        total_value_usdt += total * btc_price
                    elif asset == 'ETH' and 'ETHUSDT' in data.get('market_prices', {}):
                        eth_price = float(data['market_prices']['ETHUSDT'].get('lastPrice', 0))
                        total_value_usdt += total * eth_price
        
        # 处理最近交易
        recent_trades_formatted = []
        for symbol, trades in data.get('recent_trades', {}).items():
            if trades:
                for trade in trades[-5:]:  # 最近5笔
                    trade_time = datetime.fromtimestamp(trade['time']/1000)
                    recent_trades_formatted.append({
                        'time': trade_time.strftime('%H:%M:%S'),
                        'symbol': symbol,
                        'side': '买入' if trade['isBuyer'] else '卖出',
                        'quantity': float(trade['qty']),
                        'price': float(trade['price']),
                        'value': float(trade['quoteQty'])
                    })
        
        # 按时间排序
        recent_trades_formatted.sort(key=lambda x: x['time'], reverse=True)
        
        return {
            'account_type': account.get('accountType', 'N/A'),
            'permissions': account.get('permissions', []),
            'balances': balances,
            'total_value_usdt': total_value_usdt,
            'open_orders': data.get('open_orders', []),
            'recent_trades': recent_trades_formatted[:10],
            'market_prices': data.get('market_prices', {}),
            'system_status': data.get('system_status', 'Unknown'),
            'last_update': data.get('last_update'),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_production_dashboard_html(self):
        """生成生产环境监控面板HTML"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>TradeFan 生产环境监控</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: #c0392b; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 1.8em; font-weight: bold; color: #27ae60; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        .balance-item { display: flex; justify-content: space-between; margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; }
        .trades-table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .trades-table table { width: 100%; border-collapse: collapse; }
        .trades-table th, .trades-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        .trades-table th { background: #2c3e50; color: white; }
        .trade-buy { color: #27ae60; font-weight: bold; }
        .trade-sell { color: #e74c3c; font-weight: bold; }
        .refresh-btn { background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .status-running { color: #27ae60; font-weight: bold; }
        .status-stopped { color: #e74c3c; font-weight: bold; }
        .price-up { color: #27ae60; }
        .price-down { color: #e74c3c; }
        .production-badge { background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔴 TradeFan 生产环境监控 <span class="production-badge">LIVE</span></h1>
            <p>实时监控真实交易数据 | 系统状态: <span id="system-status">检查中...</span></p>
            <button class="refresh-btn" onclick="refreshData()">🔄 刷新数据</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>💰 账户总价值</h3>
                <div class="stat-value" id="total-value">$0.00</div>
                <div class="stat-label">USDT等值</div>
            </div>
            <div class="stat-card">
                <h3>📊 账户类型</h3>
                <div class="stat-value" id="account-type">-</div>
                <div class="stat-label" id="permissions">权限检查中...</div>
            </div>
            <div class="stat-card">
                <h3>📋 当前挂单</h3>
                <div class="stat-value" id="open-orders-count">0</div>
                <div class="stat-label">活跃订单数</div>
            </div>
            <div class="stat-card">
                <h3>⏰ 最后更新</h3>
                <div class="stat-value" id="last-update">-</div>
                <div class="stat-label">数据更新时间</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>💳 账户余额</h3>
                <div id="balances-list">
                    <div class="balance-item">
                        <span>加载中...</span>
                    </div>
                </div>
            </div>
            <div class="stat-card">
                <h3>💹 市场价格</h3>
                <div id="market-prices">
                    <div class="balance-item">
                        <span>BTC/USDT:</span>
                        <span id="btc-price">$0.00 (0%)</span>
                    </div>
                    <div class="balance-item">
                        <span>ETH/USDT:</span>
                        <span id="eth-price">$0.00 (0%)</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="trades-table">
            <h3 style="margin: 0; padding: 20px; background: #2c3e50; color: white;">📈 最近交易记录 (真实交易)</h3>
            <table>
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>交易对</th>
                        <th>方向</th>
                        <th>数量</th>
                        <th>价格</th>
                        <th>金额</th>
                    </tr>
                </thead>
                <tbody id="trades-tbody">
                    <tr><td colspan="6" style="text-align: center; color: #7f8c8d;">加载交易记录...</td></tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function refreshData() {
            fetch('/api/production-stats')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        function updateDashboard(data) {
            // 更新系统状态
            const statusElement = document.getElementById('system-status');
            statusElement.textContent = data.system_status;
            statusElement.className = data.system_status === 'Running' ? 'status-running' : 'status-stopped';
            
            // 更新账户信息
            document.getElementById('total-value').textContent = '$' + data.total_value_usdt.toFixed(2);
            document.getElementById('account-type').textContent = data.account_type;
            document.getElementById('permissions').textContent = data.permissions.join(', ') || '无特殊权限';
            document.getElementById('open-orders-count').textContent = data.open_orders.length;
            
            if (data.last_update) {
                const updateTime = new Date(data.last_update);
                document.getElementById('last-update').textContent = updateTime.toLocaleTimeString();
            }
            
            // 更新余额
            const balancesList = document.getElementById('balances-list');
            balancesList.innerHTML = '';
            
            for (const [asset, balance] of Object.entries(data.balances)) {
                const balanceItem = document.createElement('div');
                balanceItem.className = 'balance-item';
                
                let displayValue = balance.total.toFixed(asset === 'USDT' ? 2 : 6);
                balanceItem.innerHTML = `
                    <span>${asset}:</span>
                    <span>${displayValue} ${balance.locked > 0 ? '(冻结: ' + balance.locked.toFixed(6) + ')' : ''}</span>
                `;
                balancesList.appendChild(balanceItem);
            }
            
            // 更新市场价格
            if (data.market_prices.BTCUSDT) {
                const btcData = data.market_prices.BTCUSDT;
                const btcPrice = parseFloat(btcData.lastPrice);
                const btcChange = parseFloat(btcData.priceChangePercent);
                document.getElementById('btc-price').innerHTML = 
                    `$${btcPrice.toFixed(2)} <span class="${btcChange >= 0 ? 'price-up' : 'price-down'}">(${btcChange.toFixed(2)}%)</span>`;
            }
            
            if (data.market_prices.ETHUSDT) {
                const ethData = data.market_prices.ETHUSDT;
                const ethPrice = parseFloat(ethData.lastPrice);
                const ethChange = parseFloat(ethData.priceChangePercent);
                document.getElementById('eth-price').innerHTML = 
                    `$${ethPrice.toFixed(2)} <span class="${ethChange >= 0 ? 'price-up' : 'price-down'}">(${ethChange.toFixed(2)}%)</span>`;
            }
            
            // 更新交易记录
            const tbody = document.getElementById('trades-tbody');
            if (data.recent_trades.length > 0) {
                tbody.innerHTML = data.recent_trades.map(trade => 
                    `<tr>
                        <td>${trade.time}</td>
                        <td>${trade.symbol}</td>
                        <td class="trade-${trade.side === '买入' ? 'buy' : 'sell'}">${trade.side}</td>
                        <td>${trade.quantity.toFixed(6)}</td>
                        <td>$${trade.price.toFixed(2)}</td>
                        <td>$${trade.value.toFixed(2)}</td>
                    </tr>`
                ).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #7f8c8d;">暂无交易记录</td></tr>';
            }
        }
        
        // 自动刷新
        setInterval(refreshData, 30000);  // 每30秒刷新
        
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
    print("🔴 TradeFan 生产环境Web监控")
    print("=" * 40)
    
    try:
        monitor = ProductionWebMonitor()
        
        print("🌐 启动生产环境监控面板...")
        print("📊 访问地址: http://localhost:8081")
        print("💡 按 Ctrl+C 停止监控")
        print()
        
        monitor.start_web_server()
        
    except KeyboardInterrupt:
        print("\n⚠️ 监控被用户中断")
        return 0
    except Exception as e:
        print(f"\n❌ 监控启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
