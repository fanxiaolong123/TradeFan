"""
Web监控面板主应用
基于FastAPI的交易系统监控界面
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

try:
    from fastapi import FastAPI, WebSocket, Request
    from fastapi.templating import Jinja2Templates
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

import pandas as pd

from core.config_manager import ConfigManager
from core.logger import LoggerManager


class WebDashboard:
    """
    Web监控面板
    提供实时交易数据监控、性能分析和系统状态查看
    """
    
    def __init__(self, config_manager: ConfigManager, logger_manager: LoggerManager):
        """
        初始化Web监控面板
        
        Args:
            config_manager: 配置管理器
            logger_manager: 日志管理器
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError("需要安装 FastAPI 和相关依赖: pip install fastapi uvicorn jinja2")
        
        self.config_manager = config_manager
        self.logger_manager = logger_manager
        self.logger = logger_manager.get_logger('web_dashboard')
        
        # Web应用配置
        self.host = config_manager.get('monitoring.dashboard.host', '127.0.0.1')
        self.port = config_manager.get('monitoring.dashboard.port', 8080)
        self.debug = config_manager.get('monitoring.dashboard.debug', False)
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title="TradeFan 监控面板",
            description="量化交易系统实时监控",
            version="2.0.0"
        )
        
        # 模板和静态文件
        self.templates = Jinja2Templates(directory="monitoring/dashboard/templates")
        
        # 连接的WebSocket客户端
        self.connected_clients: List[WebSocket] = []
        
        # 监控数据缓存
        self.trading_data: Dict[str, Any] = {
            'positions': {},
            'orders': [],
            'performance': {},
            'alerts': [],
            'system_status': {}
        }
        
        # 设置路由
        self._setup_routes()
        
        self.logger.info("Web监控面板初始化完成")
    
    def _setup_routes(self):
        """设置Web路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """主监控页面"""
            return self.templates.TemplateResponse(
                "dashboard.html", 
                {"request": request, "title": "TradeFan 监控面板"}
            )
        
        @self.app.get("/api/status")
        async def get_system_status():
            """获取系统状态"""
            return {
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "uptime": str(datetime.now() - self.start_time) if hasattr(self, 'start_time') else "0:00:00",
                "data": self.trading_data['system_status']
            }
        
        @self.app.get("/api/positions")
        async def get_positions():
            """获取当前持仓"""
            return {
                "timestamp": datetime.now().isoformat(),
                "positions": self.trading_data['positions']
            }
        
        @self.app.get("/api/performance")
        async def get_performance():
            """获取交易性能"""
            return {
                "timestamp": datetime.now().isoformat(),
                "performance": self.trading_data['performance']
            }
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            """获取告警信息"""
            return {
                "timestamp": datetime.now().isoformat(),
                "alerts": self.trading_data['alerts'][-100:]  # 最近100条告警
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket连接端点"""
            await self.handle_websocket(websocket)
    
    async def handle_websocket(self, websocket: WebSocket):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
        """
        await websocket.accept()
        self.connected_clients.append(websocket)
        
        try:
            # 发送初始数据
            await websocket.send_json({
                "type": "init",
                "data": self.trading_data
            })
            
            # 保持连接
            while True:
                try:
                    # 接收客户端消息
                    data = await websocket.receive_json()
                    await self.handle_client_message(websocket, data)
                except Exception as e:
                    self.logger.error(f"WebSocket消息处理错误: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
        finally:
            # 移除断开的客户端
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)
    
    async def handle_client_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        处理客户端消息
        
        Args:
            websocket: WebSocket连接
            message: 客户端消息
        """
        msg_type = message.get('type')
        
        if msg_type == 'subscribe':
            # 订阅特定数据类型
            data_type = message.get('data_type')
            await websocket.send_json({
                "type": "subscribed",
                "data_type": data_type,
                "message": f"已订阅 {data_type} 数据"
            })
        
        elif msg_type == 'ping':
            # 心跳检测
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
    
    async def broadcast_update(self, data_type: str, data: Any):
        """
        向所有连接的客户端广播更新
        
        Args:
            data_type: 数据类型
            data: 更新数据
        """
        if not self.connected_clients:
            return
        
        message = {
            "type": "update",
            "data_type": data_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # 向所有客户端发送更新
        disconnected_clients = []
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                self.logger.error(f"向客户端发送数据失败: {e}")
                disconnected_clients.append(client)
        
        # 移除断开的客户端
        for client in disconnected_clients:
            self.connected_clients.remove(client)
    
    def update_trading_data(self, data_type: str, data: Any):
        """
        更新交易数据
        
        Args:
            data_type: 数据类型 (positions, orders, performance, alerts, system_status)
            data: 数据内容
        """
        if data_type in self.trading_data:
            self.trading_data[data_type] = data
            
            # 异步广播更新
            asyncio.create_task(self.broadcast_update(data_type, data))
    
    def add_alert(self, level: str, message: str, details: Optional[Dict] = None):
        """
        添加告警
        
        Args:
            level: 告警级别 (info, warning, error, critical)
            message: 告警消息
            details: 详细信息
        """
        alert = {
            'id': len(self.trading_data['alerts']) + 1,
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'details': details or {}
        }
        
        self.trading_data['alerts'].append(alert)
        
        # 只保留最近1000条告警
        if len(self.trading_data['alerts']) > 1000:
            self.trading_data['alerts'] = self.trading_data['alerts'][-1000:]
        
        # 广播告警
        asyncio.create_task(self.broadcast_update('alerts', [alert]))
        
        self.logger.info(f"添加告警 [{level}]: {message}")
    
    async def start(self):
        """启动Web监控面板"""
        self.start_time = datetime.now()
        
        try:
            self.logger.info(f"启动Web监控面板: http://{self.host}:{self.port}")
            
            config = uvicorn.Config(
                self.app, 
                host=self.host, 
                port=self.port,
                log_level="info" if self.debug else "warning"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"Web监控面板启动失败: {e}")
            raise
    
    async def stop(self):
        """停止Web监控面板"""
        self.logger.info("Web监控面板已停止")
        
        # 关闭所有WebSocket连接
        for client in self.connected_clients:
            await client.close()
        self.connected_clients.clear()


def create_dashboard(config_manager: ConfigManager, logger_manager: LoggerManager) -> WebDashboard:
    """
    创建Web监控面板实例
    
    Args:
        config_manager: 配置管理器
        logger_manager: 日志管理器
        
    Returns:
        WebDashboard: Web监控面板实例
    """
    return WebDashboard(config_manager, logger_manager)