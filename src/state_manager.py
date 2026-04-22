#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理器
负责管理应用程序的响应式状态
"""

import json
import os
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime


class StateManager:
    """
    状态管理器类
    管理应用程序的所有响应式状态
    """
    
    def __init__(self, config_path: str):
        """
        初始化状态管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        
        # 串口配置
        self.serial_port: str = ""
        self.baudrate: int = 9600
        self.is_connected: bool = False
        self.connection_status: str = "未连接"
        
        # 数据状态
        self.current_box_id: str = "1"
        self.latest_data: Dict[str, Dict[str, Any]] = {}
        
        # 回调函数
        self.on_config_change: Optional[Callable] = None
        self.on_data_change: Optional[Callable] = None
        self.on_connection_change: Optional[Callable] = None
        
        # 加载配置
        self._load_config()
    
    def _load_config(self) -> None:
        """
        加载配置文件
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # 加载串口配置
                serial_config = self.config.get("serial", {})
                self.serial_port = serial_config.get("port", "")
                self.baudrate = serial_config.get("baudrate", 9600)
                
                print(f"[状态管理器] 配置文件已加载: {self.config_path}")
            else:
                # 创建默认配置
                self._create_default_config()
                print(f"[状态管理器] 配置文件不存在，已创建默认配置")
                
        except Exception as e:
            print(f"[错误] 加载配置文件失败: {e}")
            self._create_default_config()
    
    def _create_default_config(self) -> None:
        """
        创建默认配置
        """
        self.config = {
            "boxes": {
                "1": {
                    "name": "采集箱 1",
                    "remarks": [f"通道 1-{i+1}" for i in range(30)]
                },
                "2": {
                    "name": "采集箱 2",
                    "remarks": [f"通道 2-{i+1}" for i in range(30)]
                },
                "3": {
                    "name": "采集箱 3",
                    "remarks": [f"通道 3-{i+1}" for i in range(30)]
                },
                "4": {
                    "name": "采集箱 4",
                    "remarks": [f"通道 4-{i+1}" for i in range(30)]
                }
            },
            "serial": {
                "port": "",
                "baudrate": 9600
            }
        }
        self._save_config()
    
    def _save_config(self) -> None:
        """
        保存配置文件
        """
        try:
            # 更新串口配置
            self.config["serial"] = {
                "port": self.serial_port,
                "baudrate": self.baudrate
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            
            print(f"[状态管理器] 配置文件已保存: {self.config_path}")
            
            # 触发配置变更回调
            if self.on_config_change and callable(self.on_config_change):
                self.on_config_change(self.config)
                
        except Exception as e:
            print(f"[错误] 保存配置文件失败: {e}")
    
    def get_all_remarks(self) -> Dict[str, List[str]]:
        """
        获取所有采集箱的备注
        
        Returns:
            所有采集箱的备注字典，key为BoxID字符串
        """
        remarks_dict = {}
        boxes = self.config.get("boxes", {})
        
        for box_id, box_config in boxes.items():
            remarks_dict[box_id] = box_config.get("remarks", [f"通道 {box_id}-{i+1}" for i in range(30)])
        
        return remarks_dict
    
    def get_remarks(self, box_id: str) -> List[str]:
        """
        获取指定采集箱的备注
        
        Args:
            box_id: 采集箱 ID
            
        Returns:
            备注列表
        """
        boxes = self.config.get("boxes", {})
        box_config = boxes.get(str(box_id), {})
        return box_config.get("remarks", [f"通道 {box_id}-{i+1}" for i in range(30)])
    
    def get_box_name(self, box_id: str) -> str:
        """
        获取指定采集箱的名称
        
        Args:
            box_id: 采集箱 ID
            
        Returns:
            采集箱名称
        """
        boxes = self.config.get("boxes", {})
        box_config = boxes.get(str(box_id), {})
        return box_config.get("name", f"采集箱 {box_id}")
    
    def update_remark(self, box_id: str, channel_index: int, remark: str) -> None:
        """
        更新单个通道的备注
        
        Args:
            box_id: 采集箱 ID
            channel_index: 通道索引 (0-29)
            remark: 新的备注
        """
        box_id = str(box_id)
        boxes = self.config.get("boxes", {})
        
        if box_id not in boxes:
            boxes[box_id] = {
                "name": f"采集箱 {box_id}",
                "remarks": [f"通道 {box_id}-{i+1}" for i in range(30)]
            }
        
        box_config = boxes[box_id]
        remarks = box_config.get("remarks", [])
        
        # 确保备注列表长度足够
        while len(remarks) < 30:
            remarks.append(f"通道 {box_id}-{len(remarks)+1}")
        
        # 更新指定通道的备注
        if 0 <= channel_index < 30:
            remarks[channel_index] = remark
            box_config["remarks"] = remarks
        
        # 保存配置
        self._save_config()
    
    def update_all_remarks(self, box_id: str, remarks: List[str]) -> None:
        """
        更新指定采集箱的所有备注
        
        Args:
            box_id: 采集箱 ID
            remarks: 新的备注列表 (30个)
        """
        box_id = str(box_id)
        boxes = self.config.get("boxes", {})
        
        if box_id not in boxes:
            boxes[box_id] = {
                "name": f"采集箱 {box_id}",
                "remarks": [f"通道 {box_id}-{i+1}" for i in range(30)]
            }
        
        box_config = boxes[box_id]
        
        # 确保备注列表长度为30
        while len(remarks) < 30:
            remarks.append(f"通道 {box_id}-{len(remarks)+1}")
        
        box_config["remarks"] = remarks[:30]
        
        # 保存配置
        self._save_config()
    
    def update_box_name(self, box_id: str, name: str) -> None:
        """
        更新采集箱名称
        
        Args:
            box_id: 采集箱 ID
            name: 新的名称
        """
        box_id = str(box_id)
        boxes = self.config.get("boxes", {})
        
        if box_id not in boxes:
            boxes[box_id] = {
                "name": name,
                "remarks": [f"通道 {box_id}-{i+1}" for i in range(30)]
            }
        else:
            boxes[box_id]["name"] = name
        
        # 保存配置
        self._save_config()
    
    def update_serial_config(self, port: str, baudrate: int) -> None:
        """
        更新串口配置
        
        Args:
            port: 串口名称
            baudrate: 波特率
        """
        self.serial_port = port
        self.baudrate = baudrate
        
        # 保存配置
        self._save_config()
    
    def set_connection_status(self, connected: bool, status: str = "") -> None:
        """
        设置连接状态
        
        Args:
            connected: 是否已连接
            status: 状态描述
        """
        self.is_connected = connected
        self.connection_status = status if status else ("已连接" if connected else "未连接")
        
        # 触发连接状态变更回调
        if self.on_connection_change and callable(self.on_connection_change):
            self.on_connection_change(connected, self.connection_status)
    
    def update_latest_data(self, box_id: str, data: Dict[str, Any]) -> None:
        """
        更新最新数据
        
        Args:
            box_id: 采集箱 ID
            data: 数据字典
        """
        box_id = str(box_id)
        self.latest_data[box_id] = data
        self.current_box_id = box_id  # 更新当前显示的BoxID
        
        # 触发数据变更回调
        if self.on_data_change and callable(self.on_data_change):
            self.on_data_change(box_id, data)
    
    def get_latest_data(self, box_id: str = None) -> Dict[str, Any]:
        """
        获取最新数据
        
        Args:
            box_id: 采集箱 ID，如果为None则返回当前BoxID的数据
            
        Returns:
            数据字典
        """
        if box_id is None:
            box_id = self.current_box_id
        return self.latest_data.get(str(box_id), {})
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取完整配置
        
        Returns:
            配置字典
        """
        return self.config.copy()
