"""
通知系统模块
支持Telegram、邮件等多种通知方式
"""

import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from .log_module import LogModule

class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config: Dict, logger: LogModule = None):
        self.config = config
        self.logger = logger or LogModule()
        
        # 通知配置
        self.telegram_config = config.get('telegram', {})
        self.email_config = config.get('email', {})
        
        self.logger.info("通知管理器初始化完成")
    
    def send_notification(self, message: str, title: str = "交易系统通知", 
                         channels: List[str] = None, priority: str = "normal"):
        """发送通知"""
        if channels is None:
            channels = ["telegram", "email"]
        
        success_count = 0
        
        for channel in channels:
            try:
                if channel == "telegram" and self.telegram_config.get('enabled', False):
                    if self._send_telegram(message, title):
                        success_count += 1
                elif channel == "email" and self.email_config.get('enabled', False):
                    if self._send_email(message, title):
                        success_count += 1
            except Exception as e:
                self.logger.error(f"通知发送失败 ({channel}): {e}")
        
        if success_count > 0:
            self.logger.info(f"通知发送成功: {success_count}/{len(channels)} 个渠道")
        else:
            self.logger.warning("所有通知渠道发送失败")
        
        return success_count > 0
    
    def _send_telegram(self, message: str, title: str) -> bool:
        """发送Telegram通知"""
        try:
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            
            if not bot_token or not chat_id:
                self.logger.warning("Telegram配置不完整")
                return False
            
            # 格式化消息
            formatted_message = f"🤖 *{title}*\n\n{message}"
            
            # 发送消息
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': formatted_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Telegram通知发送成功")
                return True
            else:
                self.logger.error(f"Telegram通知发送失败: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Telegram通知发送异常: {e}")
            return False
    
    def _send_email(self, message: str, title: str) -> bool:
        """发送邮件通知"""
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            to_email = self.email_config.get('to_email')
            
            if not all([smtp_server, username, password, to_email]):
                self.logger.warning("邮件配置不完整")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = f"[交易系统] {title}"
            
            # 邮件内容
            body = f"""
交易系统通知

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
标题: {title}

内容:
{message}

---
此邮件由自动交易系统发送
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info("邮件通知发送成功")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件通知发送异常: {e}")
            return False
    
    def send_trade_notification(self, trade_info: Dict):
        """发送交易通知"""
        symbol = trade_info.get('symbol', 'Unknown')
        side = trade_info.get('side', 'Unknown')
        amount = trade_info.get('amount', 0)
        price = trade_info.get('price', 0)
        
        message = f"""
📊 交易执行通知

币种: {symbol}
方向: {'🟢 买入' if side == 'buy' else '🔴 卖出'}
数量: {amount}
价格: ${price:.2f}
总价值: ${amount * price:.2f}

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_notification(message, "交易执行", priority="high")
    
    def send_alert_notification(self, alert_type: str, details: Dict):
        """发送报警通知"""
        alert_messages = {
            'drawdown': f"⚠️ 回撤报警\n当前回撤: {details.get('current_drawdown', 0):.2%}\n阈值: {details.get('threshold', 0):.2%}",
            'daily_loss': f"⚠️ 日亏损报警\n当日亏损: {details.get('daily_loss', 0):.2%}\n阈值: {details.get('threshold', 0):.2%}",
            'position_size': f"⚠️ 仓位报警\n{details.get('symbol', 'Unknown')} 仓位: {details.get('position_size', 0):.2%}\n阈值: {details.get('threshold', 0):.2%}",
            'system_error': f"🚨 系统错误\n错误信息: {details.get('error', 'Unknown error')}"
        }
        
        message = alert_messages.get(alert_type, f"未知报警类型: {alert_type}")
        
        self.send_notification(message, "系统报警", priority="urgent")
    
    def send_daily_report(self, report_data: Dict):
        """发送日报"""
        message = f"""
📈 交易系统日报

日期: {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}

📊 今日表现:
• 总收益: {report_data.get('daily_return', 0):.2%}
• 交易次数: {report_data.get('trade_count', 0)}
• 胜率: {report_data.get('win_rate', 0):.1%}
• 最大回撤: {report_data.get('max_drawdown', 0):.2%}

💰 账户状态:
• 总资产: ${report_data.get('total_balance', 0):.2f}
• 可用资金: ${report_data.get('available_balance', 0):.2f}
• 持仓价值: ${report_data.get('position_value', 0):.2f}

🎯 持仓情况:
        """
        
        positions = report_data.get('positions', {})
        for symbol, position in positions.items():
            if position.get('size', 0) > 0:
                pnl = position.get('unrealized_pnl', 0)
                pnl_pct = position.get('pnl_percent', 0)
                message += f"• {symbol}: {position['size']:.6f} (盈亏: ${pnl:.2f} / {pnl_pct:+.2%})\n"
        
        if not positions:
            message += "• 当前无持仓\n"
        
        self.send_notification(message, "每日报告")

class AlertManager:
    """报警管理器"""
    
    def __init__(self, config: Dict, notification_manager: NotificationManager, logger: LogModule = None):
        self.config = config
        self.notification_manager = notification_manager
        self.logger = logger or LogModule()
        
        # 报警配置
        self.alerts_config = config.get('alerts', {})
        self.conditions = self.alerts_config.get('conditions', [])
        
        # 报警状态跟踪
        self.alert_states = {}
        self.last_alert_times = {}
        
        self.logger.info("报警管理器初始化完成")
    
    def check_alerts(self, system_status: Dict):
        """检查报警条件"""
        if not self.alerts_config.get('enabled', False):
            return
        
        for condition in self.conditions:
            try:
                self._check_single_condition(condition, system_status)
            except Exception as e:
                self.logger.error(f"报警检查失败: {e}")
    
    def _check_single_condition(self, condition: Dict, system_status: Dict):
        """检查单个报警条件"""
        alert_type = condition.get('type')
        threshold = condition.get('threshold')
        
        if not condition.get('enabled', True):
            return
        
        current_time = datetime.now()
        alert_key = f"{alert_type}_{threshold}"
        
        # 避免重复报警（5分钟内不重复）
        if alert_key in self.last_alert_times:
            time_diff = (current_time - self.last_alert_times[alert_key]).total_seconds()
            if time_diff < 300:  # 5分钟
                return
        
        triggered = False
        details = {}
        
        if alert_type == 'drawdown':
            current_drawdown = system_status.get('max_drawdown', 0)
            if abs(current_drawdown) > threshold:
                triggered = True
                details = {
                    'current_drawdown': current_drawdown,
                    'threshold': threshold
                }
        
        elif alert_type == 'daily_loss':
            daily_loss = system_status.get('daily_return', 0)
            if daily_loss < -threshold:
                triggered = True
                details = {
                    'daily_loss': daily_loss,
                    'threshold': threshold
                }
        
        elif alert_type == 'position_size':
            positions = system_status.get('positions', {})
            for symbol, position in positions.items():
                position_size = abs(position.get('size_percent', 0))
                if position_size > threshold:
                    triggered = True
                    details = {
                        'symbol': symbol,
                        'position_size': position_size,
                        'threshold': threshold
                    }
                    break
        
        elif alert_type == 'system_error':
            if system_status.get('has_error', False):
                triggered = True
                details = {
                    'error': system_status.get('last_error', 'Unknown error')
                }
        
        if triggered:
            self.notification_manager.send_alert_notification(alert_type, details)
            self.last_alert_times[alert_key] = current_time
            self.logger.warning(f"触发报警: {alert_type}")

class ReportManager:
    """报告管理器"""
    
    def __init__(self, notification_manager: NotificationManager, logger: LogModule = None):
        self.notification_manager = notification_manager
        self.logger = logger or LogModule()
        
        self.last_daily_report = None
        
        self.logger.info("报告管理器初始化完成")
    
    def should_send_daily_report(self) -> bool:
        """检查是否应该发送日报"""
        current_date = datetime.now().date()
        
        if self.last_daily_report != current_date:
            return True
        
        return False
    
    def generate_daily_report(self, system_status: Dict) -> Dict:
        """生成日报数据"""
        current_date = datetime.now().date()
        
        report_data = {
            'date': current_date.strftime('%Y-%m-%d'),
            'daily_return': system_status.get('daily_return', 0),
            'trade_count': system_status.get('trade_count', 0),
            'win_rate': system_status.get('win_rate', 0),
            'max_drawdown': system_status.get('max_drawdown', 0),
            'total_balance': system_status.get('total_balance', 0),
            'available_balance': system_status.get('available_balance', 0),
            'position_value': system_status.get('position_value', 0),
            'positions': system_status.get('positions', {})
        }
        
        return report_data
    
    def send_daily_report_if_needed(self, system_status: Dict):
        """如果需要则发送日报"""
        if self.should_send_daily_report():
            report_data = self.generate_daily_report(system_status)
            self.notification_manager.send_daily_report(report_data)
            self.last_daily_report = datetime.now().date()
            self.logger.info("已发送日报")
