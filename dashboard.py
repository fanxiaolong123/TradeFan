#!/usr/bin/env python3
"""
交易系统监控仪表板
提供Web界面监控交易状态
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import sys
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.utils import ConfigLoader
from modules.log_module import LogModule

app = Flask(__name__)

class TradingDashboard:
    """交易监控仪表板"""
    
    def __init__(self):
        self.config = ConfigLoader()
        self.logger = LogModule()
        
        # 模拟数据存储（实际应该连接到交易系统）
        self.mock_data = self._generate_mock_data()
    
    def _generate_mock_data(self):
        """生成模拟数据"""
        return {
            'balance': {
                'USDT': {'free': 8500.50, 'used': 1499.50, 'total': 10000.00},
                'BTC': {'free': 0.025, 'used': 0, 'total': 0.025},
                'ETH': {'free': 0.8, 'used': 0, 'total': 0.8}
            },
            'positions': {
                'BTC/USDT': {
                    'size': 0.025,
                    'entry_price': 45000.00,
                    'current_price': 46500.00,
                    'unrealized_pnl': 37.50,
                    'pnl_percent': 3.33
                },
                'ETH/USDT': {
                    'size': 0.8,
                    'entry_price': 2800.00,
                    'current_price': 2850.00,
                    'unrealized_pnl': 40.00,
                    'pnl_percent': 1.79
                }
            },
            'recent_trades': [
                {
                    'timestamp': '2025-07-11 16:30:00',
                    'symbol': 'BTC/USDT',
                    'side': 'buy',
                    'amount': 0.025,
                    'price': 45000.00,
                    'status': 'filled'
                },
                {
                    'timestamp': '2025-07-11 15:45:00',
                    'symbol': 'ETH/USDT',
                    'side': 'buy',
                    'amount': 0.8,
                    'price': 2800.00,
                    'status': 'filled'
                }
            ],
            'stats': {
                'total_trades': 15,
                'successful_trades': 13,
                'failed_trades': 2,
                'win_rate': 86.67,
                'total_pnl': 125.50,
                'total_commission': 12.45
            }
        }

# 创建仪表板实例
dashboard = TradingDashboard()

@app.route('/')
def index():
    """主页"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'uptime': '2h 15m'
    })

@app.route('/api/balance')
def get_balance():
    """获取账户余额"""
    return jsonify(dashboard.mock_data['balance'])

@app.route('/api/positions')
def get_positions():
    """获取持仓信息"""
    return jsonify(dashboard.mock_data['positions'])

@app.route('/api/trades')
def get_trades():
    """获取交易记录"""
    return jsonify(dashboard.mock_data['recent_trades'])

@app.route('/api/stats')
def get_stats():
    """获取交易统计"""
    return jsonify(dashboard.mock_data['stats'])

@app.route('/api/prices')
def get_prices():
    """获取价格数据"""
    # 生成模拟价格数据
    import random
    import time
    
    now = int(time.time() * 1000)
    prices = []
    
    for i in range(100):
        timestamp = now - (100 - i) * 60000  # 每分钟一个数据点
        price = 45000 + random.uniform(-1000, 1000)
        prices.append([timestamp, price])
    
    return jsonify({
        'BTC/USDT': prices,
        'ETH/USDT': [[t, p * 0.06] for t, p in prices]  # ETH价格约为BTC的6%
    })

# 创建模板目录和文件
def create_templates():
    """创建HTML模板"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>交易系统监控仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #e5e7eb;
        }
        
        .card h3 {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #374151;
        }
        
        .balance-item, .position-item, .trade-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid #f3f4f6;
        }
        
        .balance-item:last-child, .position-item:last-child, .trade-item:last-child {
            border-bottom: none;
        }
        
        .positive {
            color: #059669;
        }
        
        .negative {
            color: #dc2626;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
        
        .stat-item {
            text-align: center;
            padding: 1rem;
            background: #f9fafb;
            border-radius: 8px;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1f2937;
        }
        
        .stat-label {
            font-size: 0.875rem;
            color: #6b7280;
            margin-top: 0.25rem;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }
        
        .refresh-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background-color 0.2s;
        }
        
        .refresh-btn:hover {
            background: #2563eb;
        }
        
        .timestamp {
            font-size: 0.75rem;
            color: #9ca3af;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 自动交易系统监控</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span id="status-text">系统运行中</span>
            <span class="timestamp" id="last-update"></span>
        </div>
    </div>
    
    <div class="container">
        <div class="grid">
            <!-- 账户余额 -->
            <div class="card">
                <h3>💰 账户余额</h3>
                <div id="balance-list"></div>
            </div>
            
            <!-- 持仓信息 -->
            <div class="card">
                <h3>📋 持仓信息</h3>
                <div id="positions-list"></div>
            </div>
            
            <!-- 交易统计 -->
            <div class="card">
                <h3>📊 交易统计</h3>
                <div class="stats-grid" id="stats-grid"></div>
            </div>
        </div>
        
        <!-- 价格图表 -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>📈 价格走势</h3>
                <button class="refresh-btn" onclick="refreshData()">刷新数据</button>
            </div>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
        
        <!-- 最近交易 -->
        <div class="card">
            <h3>🔄 最近交易</h3>
            <div id="trades-list"></div>
        </div>
    </div>
    
    <script>
        let priceChart;
        
        // 初始化图表
        function initChart() {
            const ctx = document.getElementById('priceChart').getContext('2d');
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: [{
                        label: 'BTC/USDT',
                        data: [],
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'ETH/USDT',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'minute'
                            }
                        },
                        y: {
                            beginAtZero: false
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        // 更新余额显示
        function updateBalance(data) {
            const container = document.getElementById('balance-list');
            container.innerHTML = '';
            
            for (const [currency, info] of Object.entries(data)) {
                if (info.total > 0) {
                    const item = document.createElement('div');
                    item.className = 'balance-item';
                    item.innerHTML = `
                        <span><strong>${currency}</strong></span>
                        <span>${info.free.toFixed(4)} / ${info.total.toFixed(4)}</span>
                    `;
                    container.appendChild(item);
                }
            }
        }
        
        // 更新持仓显示
        function updatePositions(data) {
            const container = document.getElementById('positions-list');
            container.innerHTML = '';
            
            if (Object.keys(data).length === 0) {
                container.innerHTML = '<div class="position-item">无持仓</div>';
                return;
            }
            
            for (const [symbol, position] of Object.entries(data)) {
                const pnlClass = position.unrealized_pnl >= 0 ? 'positive' : 'negative';
                const item = document.createElement('div');
                item.className = 'position-item';
                item.innerHTML = `
                    <div>
                        <strong>${symbol}</strong><br>
                        <small>${position.size} @ $${position.entry_price.toFixed(2)}</small>
                    </div>
                    <div class="${pnlClass}">
                        $${position.unrealized_pnl.toFixed(2)}<br>
                        <small>${position.pnl_percent >= 0 ? '+' : ''}${position.pnl_percent.toFixed(2)}%</small>
                    </div>
                `;
                container.appendChild(item);
            }
        }
        
        // 更新统计显示
        function updateStats(data) {
            const container = document.getElementById('stats-grid');
            container.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${data.total_trades}</div>
                    <div class="stat-label">总交易</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${data.win_rate.toFixed(1)}%</div>
                    <div class="stat-label">胜率</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value ${data.total_pnl >= 0 ? 'positive' : 'negative'}">$${data.total_pnl.toFixed(2)}</div>
                    <div class="stat-label">总盈亏</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">$${data.total_commission.toFixed(2)}</div>
                    <div class="stat-label">手续费</div>
                </div>
            `;
        }
        
        // 更新交易记录
        function updateTrades(data) {
            const container = document.getElementById('trades-list');
            container.innerHTML = '';
            
            data.forEach(trade => {
                const sideClass = trade.side === 'buy' ? 'positive' : 'negative';
                const item = document.createElement('div');
                item.className = 'trade-item';
                item.innerHTML = `
                    <div>
                        <strong>${trade.symbol}</strong>
                        <span class="${sideClass}">${trade.side.toUpperCase()}</span><br>
                        <small class="timestamp">${trade.timestamp}</small>
                    </div>
                    <div>
                        ${trade.amount} @ $${trade.price.toFixed(2)}<br>
                        <small>${trade.status}</small>
                    </div>
                `;
                container.appendChild(item);
            });
        }
        
        // 更新价格图表
        function updateChart(data) {
            if (!priceChart) return;
            
            priceChart.data.datasets[0].data = data['BTC/USDT'].map(point => ({
                x: point[0],
                y: point[1]
            }));
            
            priceChart.data.datasets[1].data = data['ETH/USDT'].map(point => ({
                x: point[0],
                y: point[1]
            }));
            
            priceChart.update();
        }
        
        // 刷新所有数据
        async function refreshData() {
            try {
                const [balance, positions, stats, trades, prices] = await Promise.all([
                    fetch('/api/balance').then(r => r.json()),
                    fetch('/api/positions').then(r => r.json()),
                    fetch('/api/stats').then(r => r.json()),
                    fetch('/api/trades').then(r => r.json()),
                    fetch('/api/prices').then(r => r.json())
                ]);
                
                updateBalance(balance);
                updatePositions(positions);
                updateStats(stats);
                updateTrades(trades);
                updateChart(prices);
                
                document.getElementById('last-update').textContent = 
                    `最后更新: ${new Date().toLocaleTimeString()}`;
                    
            } catch (error) {
                console.error('数据刷新失败:', error);
            }
        }
        
        // 页面加载完成后初始化
        document.addEventListener('DOMContentLoaded', function() {
            initChart();
            refreshData();
            
            // 每30秒自动刷新
            setInterval(refreshData, 30000);
        });
    </script>
</body>
</html>'''
    
    with open(os.path.join(templates_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    """启动仪表板"""
    print("🚀 启动交易系统监控仪表板...")
    
    # 创建模板文件
    create_templates()
    
    print("📊 仪表板地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()
