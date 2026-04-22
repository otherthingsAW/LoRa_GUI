#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NiceGUI 前端界面模块
提供混凝土温度监控系统的Web界面
"""

from nicegui import ui, app
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio


class TemperatureUI:
    """
    温度监控界面类
    负责构建和管理所有UI组件
    """
    
    def __init__(self, state_manager, producer=None):
        """
        初始化UI
        
        Args:
            state_manager: 状态管理器
            producer: 数据生产者（可选）
        """
        self.state_manager = state_manager
        self.producer = producer
        
        # UI组件引用
        self.temperature_cards: List[Any] = []
        self.status_label: Optional[Any] = None
        self.current_box_label: Optional[Any] = None
        self.seq_label: Optional[Any] = None
        self.timestamp_label: Optional[Any] = None
        self.port_select: Optional[Any] = None
        self.baudrate_select: Optional[Any] = None
        self.connect_button: Optional[Any] = None
        self.remark_inputs: Dict[str, List[Any]] = {}  # 按box_id存储备注输入框
        
        # 颜色配置
        self.primary_color = '#2e7d32'  # 工业绿色
        self.secondary_color = '#1b5e20'
        self.card_bg_color = '#f1f8e9'
        self.border_color = '#4caf50'
        
        # 波特率选项
        self.baudrate_options = [9600, 19200, 38400, 57600, 115200]
        
        # 数据更新追踪
        self.last_update_time: Dict[str, str] = {}  # 每个box_id的最后更新时间
        
        # 构建UI
        self._build_ui()
        
        # 注册回调
        self.state_manager.on_data_change = self._on_data_update
        self.state_manager.on_connection_change = self._on_connection_change
        
        # 启动定时器定期刷新UI（用于确保后台数据更新能反映到UI）
        self._start_update_timer()
    
    def _build_ui(self) -> None:
        """构建整个UI界面"""
        # 设置页面标题
        ui.page_title('混凝土温度监控系统')
        
        # 自定义样式
        ui.add_head_html(f'''
        <style>
            .temperature-card {{
                background-color: {self.card_bg_color} !important;
                border: 2px solid {self.border_color} !important;
                border-radius: 8px !important;
                transition: all 0.3s ease !important;
            }}
            .temperature-card:hover {{
                transform: scale(1.02);
                box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
            }}
            .status-connected {{
                color: {self.primary_color} !important;
                font-weight: bold;
            }}
            .status-disconnected {{
                color: #d32f2f !important;
                font-weight: bold;
            }}
            .box-tab {{
                background-color: {self.card_bg_color} !important;
                border: 1px solid {self.border_color} !important;
            }}
            .box-tab-active {{
                background-color: {self.primary_color} !important;
                color: white !important;
            }}
            .custom-button {{
                background-color: {self.primary_color} !important;
                color: white !important;
            }}
            .custom-button:hover {{
                background-color: {self.secondary_color} !important;
            }}
            .header-style {{
                background: linear-gradient(90deg, {self.primary_color}, {self.secondary_color}) !important;
                color: white !important;
            }}
        </style>
        ''')
        
        # 主容器
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
            # 标题栏
            self._build_header()
            
            # 状态信息栏
            self._build_status_bar()
            
            # 主要内容区域（左右分栏）
            with ui.row().classes('w-full gap-4'):
                # 左侧：温度看板
                with ui.card().classes('flex-1 p-4'):
                    self._build_temperature_panel()
                
                # 右侧：配置面板
                with ui.card().classes('w-96 p-4'):
                    self._build_config_panel()
    
    def _build_header(self) -> None:
        """构建标题栏"""
        with ui.row().classes('w-full items-center justify-between p-4 rounded-lg header-style'):
            ui.label('混凝土温度监控系统').classes('text-2xl font-bold')
            ui.label(f'v1.0 | {datetime.now().strftime("%Y-%m-%d")}').classes('text-sm opacity-80')
    
    def _build_status_bar(self) -> None:
        """构建状态信息栏"""
        with ui.row().classes('w-full items-center justify-between p-3 bg-gray-100 rounded-lg'):
            # 连接状态
            with ui.row().classes('items-center gap-2'):
                ui.label('连接状态:').classes('font-medium')
                self.status_label = ui.label('未连接').classes('status-disconnected')
            
            # 当前采集箱
            with ui.row().classes('items-center gap-2'):
                ui.label('当前采集箱:').classes('font-medium')
                self.current_box_label = ui.label('--').classes('font-bold')
            
            # 序列号
            with ui.row().classes('items-center gap-2'):
                ui.label('序列号:').classes('font-medium')
                self.seq_label = ui.label('--').classes('font-bold')
            
            # 时间戳
            with ui.row().classes('items-center gap-2'):
                ui.label('更新时间:').classes('font-medium')
                self.timestamp_label = ui.label('--')
    
    def _build_temperature_panel(self) -> None:
        """构建温度看板"""
        # 面板标题
        ui.label('温度看板').classes('text-xl font-bold mb-4')
        
        # 采集箱切换标签
        with ui.row().classes('w-full mb-4 gap-2'):
            for box_id in ['1', '2', '3', '4']:
                box_name = self.state_manager.get_box_name(box_id)
                btn = ui.button(box_name).classes('box-tab px-4 py-2')
                btn.on('click', lambda bid=box_id: self._switch_box(bid))
        
        # 温度卡片网格
        with ui.grid(columns=6).classes('w-full gap-2') as self.temperature_grid:
            self._create_temperature_cards()
    
    def _create_temperature_cards(self) -> None:
        """创建30个温度卡片"""
        self.temperature_cards = []
        box_id = self.state_manager.current_box_id
        remarks = self.state_manager.get_remarks(box_id)
        
        for i in range(30):
            channel_num = i + 1
            remark = remarks[i] if i < len(remarks) else f'通道 {channel_num}'
            
            with ui.card().classes('temperature-card p-3 text-center') as card:
                ui.label(f'通道 {channel_num}').classes('text-sm font-medium text-gray-600')
                ui.label(remark).classes('text-xs text-gray-500 mb-1')
                temp_label = ui.label('-- °C').classes('text-lg font-bold')
                temp_label.style(f'color: {self.primary_color}')
                
                self.temperature_cards.append({
                    'card': card,
                    'temp_label': temp_label,
                    'remark': remark
                })
    
    def _build_config_panel(self) -> None:
        """构建配置面板"""
        # 面板标题
        ui.label('设备配置').classes('text-xl font-bold mb-4')
        
        # 串口配置
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label('串口配置').classes('font-bold mb-3')
            
            # 串口选择
            with ui.row().classes('w-full items-center gap-2 mb-2'):
                ui.label('串口号:').classes('w-20')
                ports = self._get_available_ports()
                # 确保value在options中
                selected_port = None
                if self.state_manager.serial_port and self.state_manager.serial_port in ports:
                    selected_port = self.state_manager.serial_port
                elif ports:
                    selected_port = ports[0]
                self.port_select = ui.select(
                    options=ports,
                    value=selected_port
                ).classes('flex-1')
                
                # 刷新按钮
                ui.button('刷新', on_click=self._refresh_ports).classes('custom-button px-3 py-1')
            
            # 波特率选择
            with ui.row().classes('w-full items-center gap-2 mb-3'):
                ui.label('波特率:').classes('w-20')
                self.baudrate_select = ui.select(
                    options=self.baudrate_options,
                    value=self.state_manager.baudrate
                ).classes('flex-1')
            
            # 连接按钮
            self.connect_button = ui.button(
                '连接',
                on_click=self._toggle_connection
            ).classes('custom-button w-full')
        
        # 备注管理
        with ui.card().classes('w-full p-4'):
            ui.label('备注管理').classes('font-bold mb-3')
            
            # 采集箱选择标签
            with ui.row().classes('w-full mb-3 gap-2'):
                for box_id in ['1', '2', '3', '4']:
                    btn = ui.button(f'采集箱 {box_id}').classes('box-tab px-3 py-1')
                    btn.on('click', lambda bid=box_id: self._show_remark_editor(bid))
            
            # 备注编辑区域
            self.remark_container = ui.column().classes('w-full')
            self._show_remark_editor('1')
    
    def _show_remark_editor(self, box_id: str) -> None:
        """
        显示指定采集箱的备注编辑器
        
        Args:
            box_id: 采集箱 ID
        """
        # 清空容器
        self.remark_container.clear()
        
        with self.remark_container:
            remarks = self.state_manager.get_remarks(box_id)
            self.remark_inputs[box_id] = []
            
            # 创建30个备注输入框，按6列5行排列
            with ui.grid(columns=3).classes('w-full gap-2'):
                for i in range(30):
                    channel_num = i + 1
                    remark = remarks[i] if i < len(remarks) else f'通道 {channel_num}'
                    
                    with ui.row().classes('items-center gap-1'):
                        ui.label(f'{channel_num}:').classes('text-xs w-6 text-right')
                        input_field = ui.input(value=remark).classes('flex-1 text-xs')
                        self.remark_inputs[box_id].append(input_field)
            
            # 保存按钮
            ui.button(
                '保存备注',
                on_click=lambda: self._save_remarks(box_id)
            ).classes('custom-button w-full mt-4')
    
    def _save_remarks(self, box_id: str) -> None:
        """
        保存指定采集箱的备注
        
        Args:
            box_id: 采集箱 ID
        """
        if box_id not in self.remark_inputs:
            return
        
        # 收集所有备注
        remarks = []
        for input_field in self.remark_inputs[box_id]:
            remarks.append(input_field.value if input_field.value else f'通道 {len(remarks)+1}')
        
        # 确保有30个备注
        while len(remarks) < 30:
            remarks.append(f'通道 {len(remarks)+1}')
        
        # 更新状态管理器
        self.state_manager.update_all_remarks(box_id, remarks)
        
        # 更新存储消费者的配置（如果有）
        if hasattr(self, 'storage_consumer') and self.storage_consumer:
            self.storage_consumer.update_remarks_config(self.state_manager.get_config())
        
        # 更新温度卡片上的备注
        self._update_card_remarks()
        
        # 显示成功提示
        ui.notify('备注已保存', type='positive')
    
    def _update_card_remarks(self) -> None:
        """更新温度卡片上的备注显示"""
        box_id = self.state_manager.current_box_id
        remarks = self.state_manager.get_remarks(box_id)
        
        # 重新创建温度卡片以更新备注
        self.temperature_grid.clear()
        with self.temperature_grid:
            self._create_temperature_cards()
        
        # 如果有最新数据，更新温度显示
        latest_data = self.state_manager.get_latest_data(box_id)
        if latest_data:
            self._update_temperature_display(box_id, latest_data)
    
    def _get_available_ports(self) -> List[str]:
        """
        获取可用串口列表
        
        Returns:
            串口名称列表
        """
        if self.producer:
            ports = self.producer.scan_available_ports()
            return [p["device"] for p in ports]
        return []
    
    def _refresh_ports(self) -> None:
        """刷新串口列表"""
        ports = self._get_available_ports()
        self.port_select.options = ports
        
        # 确保当前选中的值在新列表中
        current_value = self.port_select.value
        if current_value and current_value not in ports:
            if ports:
                self.port_select.value = ports[0]
            else:
                self.port_select.value = None
        
        self.port_select.update()
        ui.notify(f'已刷新，发现 {len(ports)} 个串口', type='info')
    
    def _toggle_connection(self) -> None:
        """切换连接状态"""
        if self.producer is None:
            ui.notify('生产者未初始化', type='negative')
            return
        
        if self.state_manager.is_connected:
            # 断开连接
            self.producer.stop()
            self.state_manager.set_connection_status(False, '已断开')
            self.connect_button.text = '连接'
        else:
            # 建立连接
            port = self.port_select.value
            baudrate = self.baudrate_select.value
            
            if not port:
                ui.notify('请选择串口号', type='warning')
                return
            
            # 更新配置
            self.state_manager.update_serial_config(port, baudrate)
            
            # 启动生产者
            self.producer.start(port, baudrate)
            self.state_manager.set_connection_status(True, '连接中...')
            self.connect_button.text = '断开'
    
    def _switch_box(self, box_id: str) -> None:
        """
        切换显示的采集箱
        
        Args:
            box_id: 采集箱 ID
        """
        self.state_manager.current_box_id = box_id
        self._update_card_remarks()
        self._update_status_display()
    
    def _on_data_update(self, box_id: str, data: Dict[str, Any]) -> None:
        """
        数据更新回调
        注意：此方法在后台线程中调用，不应该直接更新UI
        UI更新由定时器负责
        
        Args:
            box_id: 采集箱 ID
            data: 数据字典
        """
        # 记录更新时间，用于定时器检测
        self.last_update_time[box_id] = data.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    
    def _start_update_timer(self) -> None:
        """
        启动定时器定期刷新UI
        这是确保后台数据更新能反映到UI的安全方式
        """
        async def update_ui():
            """定期更新UI"""
            # 获取当前显示的采集箱
            current_box_id = self.state_manager.current_box_id
            
            # 获取最新数据
            latest_data = self.state_manager.get_latest_data(current_box_id)
            
            if latest_data:
                # 更新温度显示
                self._update_temperature_display(current_box_id, latest_data)
            
            # 更新连接状态显示
            if self.status_label:
                if self.state_manager.is_connected:
                    self.status_label.text = self.state_manager.connection_status
                    self.status_label.classes('status-connected', remove='status-disconnected')
                else:
                    self.status_label.text = self.state_manager.connection_status
                    self.status_label.classes('status-disconnected', remove='status-connected')
            
            # 更新连接按钮文本
            if self.connect_button:
                self.connect_button.text = '断开' if self.state_manager.is_connected else '连接'
        
        # 创建定时器（每100毫秒执行一次）
        ui.timer(0.1, update_ui)
    
    def _update_temperature_display(self, box_id: str, data: Dict[str, Any]) -> None:
        """
        更新温度显示
        注意：此方法应该在UI线程中调用
        
        Args:
            box_id: 采集箱 ID
            data: 数据字典
        """
        temperatures = data.get('Temperatures', [])
        
        # 如果是当前显示的采集箱，更新UI
        if box_id == self.state_manager.current_box_id:
            for i, temp in enumerate(temperatures):
                if i < len(self.temperature_cards):
                    temp_label = self.temperature_cards[i]['temp_label']
                    temp_label.text = f'{temp:.1f} °C'
                    
                    # 根据温度设置颜色（可选：超出范围时变色）
                    if temp < 0 or temp > 60:
                        temp_label.style('color: #d32f2f')  # 红色
                    else:
                        temp_label.style(f'color: {self.primary_color}')
        
        # 更新状态显示
        self._update_status_display()
    
    def _update_status_display(self) -> None:
        """更新状态栏显示"""
        box_id = self.state_manager.current_box_id
        data = self.state_manager.get_latest_data(box_id)
        
        # 更新采集箱名称
        box_name = self.state_manager.get_box_name(box_id)
        if self.current_box_label:
            self.current_box_label.text = box_name
        
        # 更新序列号和时间戳
        if data:
            if self.seq_label:
                self.seq_label.text = str(data.get('Seq', '--'))
            if self.timestamp_label:
                self.timestamp_label.text = data.get('Timestamp', '--')
    
    def _on_connection_change(self, connected: bool, status: str) -> None:
        """
        连接状态变更回调
        注意：此方法可能在后台线程中调用，UI更新由定时器负责
        
        Args:
            connected: 是否已连接
            status: 状态描述
        """
        # 状态已经在 state_manager 中更新，定时器会处理UI更新
        pass
    
    def _update_connection_display(self, connected: bool, status: str) -> None:
        """
        更新连接状态显示
        
        Args:
            connected: 是否已连接
            status: 状态描述
        """
        if self.status_label:
            self.status_label.text = status
            if connected:
                self.status_label.classes('status-connected', remove='status-disconnected')
            else:
                self.status_label.classes('status-disconnected', remove='status-connected')
        
        if self.connect_button:
            self.connect_button.text = '断开' if connected else '连接'


def create_ui(state_manager, producer=None) -> TemperatureUI:
    """
    创建UI实例
    
    Args:
        state_manager: 状态管理器
        producer: 数据生产者
        
    Returns:
        UI实例
    """
    return TemperatureUI(state_manager, producer)
