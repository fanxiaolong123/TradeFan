"""
监控模块
负责实时监控账户状态、持仓盈亏、系统运行状态等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import time
from datetime import datetime, timedelta
import threading

class MonitorModule:
    """监控模块"""
    
    def __init__(self, config: Dict, risk_control, data_module, logger=None):
        self.config = config
        self.risk_control = risk_control
        self.data_module = data_module
        self.logger = logger
        
        # 监控参数
        self.monitor_interval = 60  # 监控间隔（秒）
        self.alert_thresholds = {
            'max_drawdown': 0.15,  # 回撤警告阈值
            'position_concentration': 0.3,  # 仓位集中度警告
            'daily_loss_limit': 0.05  # 日亏损限制
        }
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_update = None
        
        # 性能统计
        self.performance_history = []
        self.alert_history = []
        
        if self.logger:
            self.logger.info("监控模块初始化完成")
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            if self.logger:
                self.logger.warning("监控已在运行中")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        if self.logger:
            self.logger.info("开始实时监控")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.logger:
            self.logger.info("监控已停止")
    
    def _monitor_loop(self):
        """监控主循环"""
        while self.is_monitoring:
            try:
                # 更新监控数据
                self._update_monitoring_data()
                
                # 检查警告条件
                self._check_alerts()
                
                # 输出状态报告
                self._print_status_report()
                
                # 等待下次监控
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"监控循环异常: {e}")
                time.sleep(self.monitor_interval)
    
    def _update_monitoring_data(self):
        """更新监控数据"""
        try:
            # 获取投资组合状态
            portfolio_status = self.risk_control.get_portfolio_status()
            
            # 获取当前价格
            current_prices = {}
            symbols = self.config.get('symbols', [])
            
            for symbol_config in symbols:
                if symbol_config.get('enabled', False):
                    symbol = symbol_config['symbol']
                    try:
                        ticker = self.data_module.get_ticker(symbol)
                        if ticker:
                            current_prices[symbol] = ticker['last']
                    except Exception as e:
                        if self.logger:
                            self.logger.debug(f"获取{symbol}价格失败: {e}")
            
            # 更新持仓未实现盈亏
            for symbol, price in current_prices.items():
                position = self.risk_control.get_position(symbol)
                if not position.is_empty():
                    position.update_unrealized_pnl(price)
            
            # 记录性能数据
            performance_data = {
                'timestamp': datetime.now(),
                'portfolio_status': portfolio_status,
                'current_prices': current_prices.copy(),
                'positions': {symbol: self.risk_control.get_position(symbol) 
                            for symbol in current_prices.keys()}
            }
            
            self.performance_history.append(performance_data)
            
            # 保持历史数据在合理范围内
            if len(self.performance_history) > 1440:  # 保留24小时数据（分钟级）
                self.performance_history = self.performance_history[-1440:]
            
            self.last_update = datetime.now()
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"更新监控数据失败: {e}")
    
    def _check_alerts(self):
        """检查警告条件"""
        try:
            if not self.performance_history:
                return
            
            latest_data = self.performance_history[-1]
            portfolio_status = latest_data['portfolio_status']
            
            alerts = []
            
            # 检查回撤警告
            current_drawdown = portfolio_status.get('current_drawdown', 0)
            if current_drawdown > self.alert_thresholds['max_drawdown']:
                alerts.append({
                    'type': 'drawdown_warning',
                    'message': f"回撤过大: {current_drawdown:.2%} > {self.alert_thresholds['max_drawdown']:.2%}",
                    'severity': 'high'
                })
            
            # 检查仓位集中度
            positions = latest_data['positions']
            total_position_value = sum(abs(pos.size * pos.entry_price) 
                                     for pos in positions.values() if not pos.is_empty())
            
            if total_position_value > 0:
                for symbol, position in positions.items():
                    if not position.is_empty():
                        concentration = abs(position.size * position.entry_price) / total_position_value
                        if concentration > self.alert_thresholds['position_concentration']:
                            alerts.append({
                                'type': 'concentration_warning',
                                'message': f"{symbol}仓位过于集中: {concentration:.2%}",
                                'severity': 'medium'
                            })
            
            # 检查日亏损限制
            if len(self.performance_history) >= 1440:  # 有足够的历史数据
                day_start_capital = self.performance_history[-1440]['portfolio_status'].get('current_capital', 0)
                current_capital = portfolio_status.get('current_capital', 0)
                
                if day_start_capital > 0:
                    daily_return = (current_capital - day_start_capital) / day_start_capital
                    if daily_return < -self.alert_thresholds['daily_loss_limit']:
                        alerts.append({
                            'type': 'daily_loss_warning',
                            'message': f"日亏损过大: {daily_return:.2%}",
                            'severity': 'high'
                        })
            
            # 处理警告
            for alert in alerts:
                self._handle_alert(alert)
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"检查警告失败: {e}")
    
    def _handle_alert(self, alert: Dict):
        """处理警告"""
        try:
            # 记录警告历史
            alert['timestamp'] = datetime.now()
            self.alert_history.append(alert)
            
            # 输出警告日志
            if alert['severity'] == 'high':
                if self.logger:
                    self.logger.error(f"严重警告: {alert['message']}")
            elif alert['severity'] == 'medium':
                if self.logger:
                    self.logger.warning(f"警告: {alert['message']}")
            else:
                if self.logger:
                    self.logger.info(f"提示: {alert['message']}")
            
            # 这里可以添加其他警告处理逻辑，如发送邮件、短信等
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"处理警告失败: {e}")
    
    def _print_status_report(self):
        """打印状态报告"""
        try:
            if not self.performance_history:
                return
            
            latest_data = self.performance_history[-1]
            portfolio_status = latest_data['portfolio_status']
            positions = latest_data['positions']
            current_prices = latest_data['current_prices']
            
            # 构建报告
            report_lines = []
            report_lines.append("=" * 60)
            report_lines.append(f"交易系统监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append("=" * 60)
            
            # 账户概况
            report_lines.append("账户概况:")
            report_lines.append(f"  当前资金: {portfolio_status.get('current_capital', 0):,.2f} USDT")
            report_lines.append(f"  初始资金: {portfolio_status.get('initial_capital', 0):,.2f} USDT")
            report_lines.append(f"  总收益率: {portfolio_status.get('total_return', 0):.2%}")
            report_lines.append(f"  当前回撤: {portfolio_status.get('current_drawdown', 0):.2%}")
            report_lines.append(f"  未实现盈亏: {portfolio_status.get('unrealized_pnl', 0):,.2f} USDT")
            report_lines.append(f"  已实现盈亏: {portfolio_status.get('realized_pnl', 0):,.2f} USDT")
            
            # 持仓详情
            report_lines.append("\n持仓详情:")
            active_positions = {symbol: pos for symbol, pos in positions.items() if not pos.is_empty()}
            
            if active_positions:
                for symbol, position in active_positions.items():
                    current_price = current_prices.get(symbol, 0)
                    pnl_pct = 0
                    if position.entry_price > 0:
                        if position.is_long():
                            pnl_pct = (current_price - position.entry_price) / position.entry_price
                        else:
                            pnl_pct = (position.entry_price - current_price) / position.entry_price
                    
                    direction = "多头" if position.is_long() else "空头"
                    report_lines.append(f"  {symbol}: {direction} {abs(position.size):.6f}")
                    report_lines.append(f"    入场价: {position.entry_price:.6f}")
                    report_lines.append(f"    当前价: {current_price:.6f}")
                    report_lines.append(f"    盈亏: {position.unrealized_pnl:.2f} USDT ({pnl_pct:.2%})")
            else:
                report_lines.append("  无持仓")
            
            # 市场价格
            report_lines.append("\n当前价格:")
            for symbol, price in current_prices.items():
                report_lines.append(f"  {symbol}: {price:.6f}")
            
            # 风险指标
            risk_metrics = self.risk_control.calculate_risk_metrics()
            if risk_metrics:
                report_lines.append("\n风险指标:")
                report_lines.append(f"  夏普比率: {risk_metrics.get('sharpe_ratio', 0):.4f}")
                report_lines.append(f"  波动率: {risk_metrics.get('volatility', 0):.2%}")
                report_lines.append(f"  最大回撤: {risk_metrics.get('max_drawdown', 0):.2%}")
                report_lines.append(f"  胜率: {risk_metrics.get('win_rate', 0):.2%}")
            
            # 最近警告
            recent_alerts = [alert for alert in self.alert_history 
                           if (datetime.now() - alert['timestamp']).seconds < 3600]  # 最近1小时
            if recent_alerts:
                report_lines.append("\n最近警告:")
                for alert in recent_alerts[-5:]:  # 显示最近5个警告
                    report_lines.append(f"  [{alert['timestamp'].strftime('%H:%M:%S')}] {alert['message']}")
            
            report_lines.append("=" * 60)
            
            # 输出报告
            report = "\n".join(report_lines)
            if self.logger:
                self.logger.info(f"\n{report}")
            else:
                print(report)
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"生成状态报告失败: {e}")
    
    def get_performance_summary(self, hours: int = 24) -> Dict:
        """获取性能摘要"""
        try:
            if not self.performance_history:
                return {}
            
            # 获取指定时间范围内的数据
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = [data for data in self.performance_history 
                          if data['timestamp'] >= cutoff_time]
            
            if not recent_data:
                return {}
            
            # 计算性能指标
            start_capital = recent_data[0]['portfolio_status'].get('current_capital', 0)
            end_capital = recent_data[-1]['portfolio_status'].get('current_capital', 0)
            
            period_return = (end_capital - start_capital) / start_capital if start_capital > 0 else 0
            
            # 计算最大回撤
            capitals = [data['portfolio_status'].get('current_capital', 0) for data in recent_data]
            peak_capital = max(capitals)
            min_capital = min(capitals)
            max_drawdown = (peak_capital - min_capital) / peak_capital if peak_capital > 0 else 0
            
            return {
                'period_hours': hours,
                'start_capital': start_capital,
                'end_capital': end_capital,
                'period_return': period_return,
                'max_drawdown': max_drawdown,
                'data_points': len(recent_data),
                'last_update': self.last_update
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取性能摘要失败: {e}")
            return {}
    
    def get_position_summary(self) -> Dict:
        """获取持仓摘要"""
        try:
            if not self.performance_history:
                return {}
            
            latest_data = self.performance_history[-1]
            positions = latest_data['positions']
            current_prices = latest_data['current_prices']
            
            summary = {
                'total_positions': 0,
                'long_positions': 0,
                'short_positions': 0,
                'total_unrealized_pnl': 0,
                'positions_detail': {}
            }
            
            for symbol, position in positions.items():
                if not position.is_empty():
                    summary['total_positions'] += 1
                    
                    if position.is_long():
                        summary['long_positions'] += 1
                    else:
                        summary['short_positions'] += 1
                    
                    summary['total_unrealized_pnl'] += position.unrealized_pnl
                    
                    current_price = current_prices.get(symbol, 0)
                    summary['positions_detail'][symbol] = {
                        'size': position.size,
                        'entry_price': position.entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': position.unrealized_pnl,
                        'direction': 'long' if position.is_long() else 'short'
                    }
            
            return summary
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取持仓摘要失败: {e}")
            return {}
    
    def export_monitoring_data(self, filepath: str, hours: int = 24):
        """导出监控数据"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = [data for data in self.performance_history 
                          if data['timestamp'] >= cutoff_time]
            
            if not recent_data:
                if self.logger:
                    self.logger.warning("没有监控数据可导出")
                return
            
            # 转换为DataFrame格式
            export_data = []
            for data in recent_data:
                row = {
                    'timestamp': data['timestamp'],
                    'current_capital': data['portfolio_status'].get('current_capital', 0),
                    'total_return': data['portfolio_status'].get('total_return', 0),
                    'current_drawdown': data['portfolio_status'].get('current_drawdown', 0),
                    'unrealized_pnl': data['portfolio_status'].get('unrealized_pnl', 0),
                    'realized_pnl': data['portfolio_status'].get('realized_pnl', 0)
                }
                
                # 添加价格数据
                for symbol, price in data['current_prices'].items():
                    row[f'{symbol}_price'] = price
                
                # 添加持仓数据
                for symbol, position in data['positions'].items():
                    row[f'{symbol}_position'] = position.size
                    row[f'{symbol}_pnl'] = position.unrealized_pnl
                
                export_data.append(row)
            
            # 保存到CSV
            df = pd.DataFrame(export_data)
            df.to_csv(filepath, index=False)
            
            if self.logger:
                self.logger.info(f"监控数据已导出到: {filepath}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"导出监控数据失败: {e}")
