#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoRa 数据生产者
负责从串口读取数据，解析后分发给所有注册的消费者
"""

import serial
import serial.tools.list_ports
import threading
import time
from typing import List, Dict, Any, Callable, Optional
from .lora_temperature_parser import LoRaTemperatureParser


class LoRaProducer:
    """
    LoRa 数据生产者类
    负责维护串口连接，读取并解析数据，分发给消费者
    """
    
    def __init__(self):
        """初始化生产者"""
        self.consumers: List[Any] = []
        self.serial_port: Optional[serial.Serial] = None
        self.parser = LoRaTemperatureParser()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.port = ""
        self.baudrate = 9600
        self.reconnect_interval = 5  # 重连间隔（秒）
        self.on_error: Optional[Callable[[str, str], None]] = None
        self.on_connect: Optional[Callable[[str, int], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
    
    def register_consumer(self, consumer: Any) -> None:
        """
        注册消费者
        
        Args:
            consumer: 消费者对象，必须实现 consume(data: dict) 方法
        """
        if consumer not in self.consumers:
            self.consumers.append(consumer)
    
    def unregister_consumer(self, consumer: Any) -> None:
        """
        注销消费者
        
        Args:
            consumer: 消费者对象
        """
        if consumer in self.consumers:
            self.consumers.remove(consumer)
    
    def _distribute_data(self, data: Dict[str, Any]) -> None:
        """
        将数据分发给所有注册的消费者
        
        Args:
            data: 解析后的数据字典
        """
        for consumer in self.consumers:
            try:
                if hasattr(consumer, 'consume') and callable(getattr(consumer, 'consume')):
                    consumer.consume(data)
            except Exception as e:
                print(f"[错误] 消费者处理数据失败: {e}")
    
    def _read_from_serial(self) -> None:
        """
        从串口读取数据的线程函数
        """
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    # 读取一个字节
                    byte_data = self.serial_port.read(1)
                    
                    if byte_data:
                        # 解析字节
                        success, parsed_data = self.parser.process_byte(byte_data[0])
                        
                        if success:
                            # 解析成功，转换 BoxID 为字符串格式
                            parsed_data["BoxID"] = str(parsed_data["BoxID"])
                            # 分发给消费者
                            self._distribute_data(parsed_data)
                    else:
                        # 无数据，短暂休眠
                        time.sleep(0.01)
                else:
                    # 串口未打开，尝试重连
                    self._try_reconnect()
                    
            except serial.SerialException as e:
                # 串口错误
                error_msg = f"串口通信错误: {str(e)}"
                print(f"[错误] {error_msg}")
                if self.on_error:
                    self.on_error("SERIAL_ERROR", error_msg)
                self._close_serial()
                self._try_reconnect()
            except Exception as e:
                # 其他错误
                error_msg = f"未知错误: {str(e)}"
                print(f"[错误] {error_msg}")
                if self.on_error:
                    self.on_error("UNKNOWN_ERROR", error_msg)
                time.sleep(0.1)
    
    def _close_serial(self) -> None:
        """关闭串口连接"""
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
                    print(f"[信息] 已断开串口连接")
                    if self.on_disconnect:
                        self.on_disconnect()
            except Exception as e:
                print(f"[错误] 关闭串口失败: {e}")
            finally:
                self.serial_port = None
    
    def _try_reconnect(self) -> None:
        """尝试重新连接串口"""
        if self.running:
            print(f"[信息] 尝试在 {self.reconnect_interval} 秒后重新连接...")
            time.sleep(self.reconnect_interval)
            if self.running:
                self._open_serial()
    
    def _open_serial(self) -> bool:
        """
        打开串口连接
        
        Returns:
            是否成功打开
        """
        try:
            if not self.port:
                print("[错误] 未指定串口")
                return False
            
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            
            # 重置解析器状态
            self.parser.reset_state()
            
            print(f"[信息] 已成功连接到串口: {self.port}, 波特率: {self.baudrate}")
            if self.on_connect:
                self.on_connect(self.port, self.baudrate)
            return True
            
        except serial.SerialException as e:
            print(f"[错误] 无法打开串口 {self.port}: {str(e)}")
            if self.on_error:
                self.on_error("SERIAL_OPEN_FAILED", f"无法打开串口 {self.port}: {str(e)}")
            return False
    
    def start(self, port: str, baudrate: int = 9600) -> bool:
        """
        启动生产者
        
        Args:
            port: 串口名称
            baudrate: 波特率
            
        Returns:
            是否成功启动
        """
        self.port = port
        self.baudrate = baudrate
        self.running = True
        
        # 尝试打开串口
        if not self._open_serial():
            print(f"[信息] 串口打开失败，将尝试自动重连...")
        
        # 启动读取线程
        self.thread = threading.Thread(target=self._read_from_serial, daemon=True)
        self.thread.start()
        
        print(f"[信息] 生产者已启动，串口: {port}, 波特率: {baudrate}")
        return True
    
    def stop(self) -> None:
        """停止生产者"""
        self.running = False
        
        # 关闭串口
        self._close_serial()
        
        # 等待线程结束
        if self.thread:
            self.thread.join(timeout=2)
        
        print("[信息] 生产者已停止")
    
    def update_serial_config(self, port: str, baudrate: int = 9600) -> None:
        """
        更新串口配置（热更新）
        
        Args:
            port: 新的串口名称
            baudrate: 新的波特率
        """
        # 如果配置没有变化，不做处理
        if port == self.port and baudrate == self.baudrate:
            return
        
        print(f"[信息] 更新串口配置: {self.port}:{self.baudrate} -> {port}:{baudrate}")
        
        # 关闭当前连接
        self._close_serial()
        
        # 更新配置
        self.port = port
        self.baudrate = baudrate
        
        # 如果正在运行，尝试打开新连接
        if self.running:
            self._open_serial()
    
    @staticmethod
    def scan_available_ports() -> List[Dict[str, str]]:
        """
        扫描系统上所有可用的串口
        
        Returns:
            可用串口列表，每个元素包含端口信息
        """
        ports = serial.tools.list_ports.comports()
        result = []
        
        for port in ports:
            result.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid
            })
        
        return result
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到串口
        
        Returns:
            是否已连接
        """
        return self.serial_port is not None and self.serial_port.is_open
