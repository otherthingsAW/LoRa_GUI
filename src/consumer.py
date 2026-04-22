#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消费者模块
定义消费者基类和具体实现
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import csv
import os
from datetime import datetime
from pathlib import Path


class BaseConsumer(ABC):
    """
    消费者基类
    所有消费者必须继承此类并实现 consume 方法
    """
    
    @abstractmethod
    def consume(self, data: Dict[str, Any]) -> None:
        """
        处理数据的方法
        
        Args:
            data: 解析后的数据字典
        """
        pass


class StorageConsumer(BaseConsumer):
    """
    存储消费者
    负责将数据持久化到 CSV 文件
    """
    
    def __init__(self, remarks_config: Dict[str, Any]):
        """
        初始化存储消费者
        
        Args:
            remarks_config: 备注配置，用于生成表头
        """
        self.remarks_config = remarks_config
        self.log_dir = self._get_log_directory()
        self.file_counters: Dict[str, int] = {}  # 每个BoxID的当前文件计数器
        self.current_files: Dict[str, str] = {}  # 每个BoxID当前使用的文件
        self.row_counts: Dict[str, int] = {}  # 每个文件的行数
        self.max_rows_per_file = 1000  # 每个文件最大行数
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        print(f"[存储消费者] 日志目录: {self.log_dir}")
    
    def _get_log_directory(self) -> str:
        """
        获取日志存储目录
        
        Returns:
            日志目录路径
        """
        # 获取 Documents 目录
        if os.name == 'nt':  # Windows
            documents_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
        else:  # Linux/Mac
            documents_path = os.path.join(os.environ.get('HOME', ''), 'Documents')
        
        # 拼接 LoRa_Log 目录
        log_dir = os.path.join(documents_path, 'LoRa_Log')
        return log_dir
    
    def _get_or_create_file(self, box_id: str) -> str:
        """
        获取或创建用于存储的 CSV 文件
        
        Args:
            box_id: 采集箱 ID
            
        Returns:
            文件路径
        """
        # 检查当前文件是否已满
        if box_id in self.current_files:
            current_file = self.current_files[box_id]
            row_count = self.row_counts.get(current_file, 0)
            
            if row_count < self.max_rows_per_file:
                return current_file
        
        # 需要创建新文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"concrete_log_box_{box_id}_{timestamp}.csv"
        filepath = os.path.join(self.log_dir, filename)
        
        # 更新计数器和当前文件
        if box_id not in self.file_counters:
            self.file_counters[box_id] = 0
        else:
            self.file_counters[box_id] += 1
        
        self.current_files[box_id] = filepath
        self.row_counts[filepath] = 0
        
        # 创建文件并写入表头
        self._write_header(filepath, box_id)
        
        print(f"[存储消费者] 创建新文件: {filepath}")
        return filepath
    
    def _write_header(self, filepath: str, box_id: str) -> None:
        """
        写入 CSV 表头
        
        Args:
            filepath: 文件路径
            box_id: 采集箱 ID
        """
        try:
            # 获取备注配置
            box_config = self.remarks_config.get("boxes", {}).get(box_id, {})
            remarks = box_config.get("remarks", [f"通道 {i+1}" for i in range(30)])
            
            # 构建表头
            headers = ["时间戳", "序列号"]
            for i, remark in enumerate(remarks):
                headers.append(f"{i+1}_{remark}")
            
            # 写入文件
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            
        except Exception as e:
            print(f"[错误] 写入 CSV 表头失败: {e}")
    
    def consume(self, data: Dict[str, Any]) -> None:
        """
        处理数据并存储到 CSV 文件
        
        Args:
            data: 解析后的数据字典
        """
        try:
            box_id = str(data.get("BoxID", "1"))
            seq = data.get("Seq", 0)
            temperatures = data.get("Temperatures", [])
            timestamp = data.get("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
            
            # 获取或创建文件
            filepath = self._get_or_create_file(box_id)
            
            # 构建行数据
            row = [timestamp, seq]
            row.extend(temperatures)
            
            # 写入文件
            with open(filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            # 更新行数计数
            self.row_counts[filepath] = self.row_counts.get(filepath, 0) + 1
            
            # 打印日志（可选，用于调试）
            # print(f"[存储消费者] 已写入数据: BoxID={box_id}, Seq={seq}, 行={self.row_counts[filepath]}")
            
        except Exception as e:
            print(f"[错误] 存储数据失败: {e}")
    
    def update_remarks_config(self, remarks_config: Dict[str, Any]) -> None:
        """
        更新备注配置
        
        Args:
            remarks_config: 新的备注配置
        """
        self.remarks_config = remarks_config
        print("[存储消费者] 备注配置已更新")


class UIConsumer(BaseConsumer):
    """
    UI 消费者
    负责更新 NiceGUI 响应式状态
    """
    
    def __init__(self):
        """初始化 UI 消费者"""
        self.latest_data: Dict[str, Any] = {}  # 存储每个 BoxID 的最新数据
        self.on_data_update = None  # 数据更新回调函数
    
    def consume(self, data: Dict[str, Any]) -> None:
        """
        处理数据并更新 UI 状态
        
        Args:
            data: 解析后的数据字典
        """
        try:
            box_id = str(data.get("BoxID", "1"))
            
            # 存储最新数据
            self.latest_data[box_id] = {
                "BoxID": box_id,
                "Seq": data.get("Seq", 0),
                "Temperatures": data.get("Temperatures", []),
                "Timestamp": data.get("Timestamp", "")
            }
            
            # 调用回调函数通知 UI 更新
            if self.on_data_update and callable(self.on_data_update):
                self.on_data_update(box_id, self.latest_data[box_id])
            
        except Exception as e:
            print(f"[错误] UI 消费者处理数据失败: {e}")
    
    def get_latest_data(self, box_id: str) -> Dict[str, Any]:
        """
        获取指定 BoxID 的最新数据
        
        Args:
            box_id: 采集箱 ID
            
        Returns:
            最新数据字典
        """
        return self.latest_data.get(box_id, {})
    
    def get_all_latest_data(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有 BoxID 的最新数据
        
        Returns:
            所有最新数据字典
        """
        return self.latest_data.copy()
