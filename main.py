#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混凝土温度监控系统主程序
整合所有模块，启动应用
"""

import os
import sys
from pathlib import Path

from nicegui import ui, app
from typing import Dict, Any

# 导入模块
from src.state_manager import StateManager
from src.producer import LoRaProducer
from src.consumer import StorageConsumer, UIConsumer
from src.ui import create_ui


class TemperatureMonitorApp:
    """
    温度监控应用主类
    整合所有模块，管理应用生命周期
    """
    
    def __init__(self):
        """初始化应用"""
        # 配置文件路径
        self.config_path = Path(__file__).parent / 'multi_box_config.json'
        
        # 初始化状态管理器
        self.state_manager = StateManager(str(self.config_path))
        
        # 初始化生产者
        self.producer = LoRaProducer()
        
        # 初始化消费者
        self.storage_consumer = StorageConsumer(self.state_manager.get_config())
        self.ui_consumer = UIConsumer()
        
        # 注册消费者到生产者
        self.producer.register_consumer(self.storage_consumer)
        self.producer.register_consumer(self.ui_consumer)
        
        # 设置UI消费者的数据更新回调
        self.ui_consumer.on_data_update = self._on_data_received
        
        # 设置生产者的连接回调
        self.producer.on_connect = self._on_producer_connect
        self.producer.on_disconnect = self._on_producer_disconnect
        self.producer.on_error = self._on_producer_error
        
        # UI实例
        self.ui_instance = None
    
    def _on_data_received(self, box_id: str, data: Dict[str, Any]) -> None:
        """
        数据接收回调
        
        Args:
            box_id: 采集箱 ID
            data: 数据字典
        """
        # 更新状态管理器
        self.state_manager.update_latest_data(box_id, data)
    
    def _on_producer_connect(self, port: str, baudrate: int) -> None:
        """
        生产者连接成功回调
        
        Args:
            port: 串口名称
            baudrate: 波特率
        """
        self.state_manager.set_connection_status(True, f'已连接: {port} @ {baudrate}')
    
    def _on_producer_disconnect(self) -> None:
        """生产者断开连接回调"""
        self.state_manager.set_connection_status(False, '已断开')
    
    def _on_producer_error(self, error_type: str, message: str) -> None:
        """
        生产者错误回调
        
        Args:
            error_type: 错误类型
            message: 错误消息
        """
        # 可以在这里添加UI通知
        pass
    
    def start(self) -> None:
        """启动应用"""
        print("=" * 60)
        print("混凝土温度监控系统")
        print("=" * 60)
        print(f"配置文件: {self.config_path}")
        print(f"日志目录: {self.storage_consumer.log_dir}")
        print("=" * 60)
        
        # 创建UI
        self.ui_instance = create_ui(self.state_manager, self.producer)
        
        # 传递存储消费者引用给UI，用于备注更新
        self.ui_instance.storage_consumer = self.storage_consumer
        
        # 注册关闭处理
        app.on_shutdown(self._on_shutdown)
        
        # 启动NiceGUI
        print("\n启动Web界面...")
        print("请在浏览器中访问: http://localhost:8080")
        print("按 Ctrl+C 停止程序\n")
        
        ui.run(title='混凝土温度监控系统', host='0.0.0.0', port=8080)
    
    def _on_shutdown(self) -> None:
        """应用关闭处理"""
        print("\n正在关闭应用...")
        
        # 停止生产者
        if self.producer:
            self.producer.stop()
        
        print("应用已关闭")


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("错误: 此程序需要 Python 3.8 或更高版本")
        sys.exit(1)
    
    # 检查必要的依赖
    try:
        import nicegui
        import serial
    except ImportError as e:
        print(f"错误: 缺少必要的依赖库: {e}")
        print("请运行: pip install nicegui pyserial")
        sys.exit(1)
    
    # 创建并启动应用
    app_instance = TemperatureMonitorApp()
    app_instance.start()


if __name__ in {"__main__", "__mp_main__"}:
    main()
