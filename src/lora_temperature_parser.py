#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoRa 温度数据帧解析器
用于从串口读取 LoRa 采集终端发送的温度数据帧并解析为 JSON 格式
"""

import serial
import serial.tools.list_ports
import json
import time
from datetime import datetime
from enum import Enum


class ParserState(Enum):
    """状态机状态枚举"""
    WAIT_FOR_HEADER_D = 0
    WAIT_FOR_HEADER_A = 1
    WAIT_FOR_HEADER_T = 2
    WAIT_FOR_BOXID = 3
    WAIT_FOR_SEQ = 4
    WAIT_FOR_LENGTH = 5
    WAIT_FOR_DATA = 6
    WAIT_FOR_CRC_HIGH = 7
    WAIT_FOR_CRC_LOW = 8
    WAIT_FOR_FOOTER_CR = 9
    WAIT_FOR_FOOTER_LF = 10


class LoRaTemperatureParser:
    """
    LoRa 温度数据帧解析器类
    
    数据帧格式（70字节）：
    - Header (3 Bytes): 'D', 'A', 'T' (ASCII)
    - BoxID (1 Byte): 采集箱序号
    - Seq (1 Byte): 帧序列号 (0-255)
    - Length (1 Byte): 负载长度，固定为 0x3C (60)
    - Data (60 Bytes): 30路温度数据，每路2字节（高八位在前）
    - CRC16 (2 Bytes): CRC-16/MODBUS 校验（校验范围：字节0到65）
    - Footer (2 Bytes): 0x0D, 0x0A (\r\n)
    """
    
    def __init__(self):
        """初始化解析器"""
        self.reset_state()
    
    def reset_state(self):
        """重置状态机和缓冲区"""
        self.state = ParserState.WAIT_FOR_HEADER_D
        self.frame_buffer = bytearray()
        self.temp_boxid = 0
        self.temp_seq = 0
        self.temp_length = 0
        self.data_bytes_remaining = 0
        self.temp_crc_high = 0
    
    @staticmethod
    def crc16_modbus(data: bytes) -> int:
        """
        CRC-16/MODBUS 校验算法
        
        Args:
            data: 需要校验的字节数据
            
        Returns:
            CRC16 校验值 (16位整数)
        """
        crc = 0xFFFF
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        
        return crc
    
    @staticmethod
    def parse_temperature_data(data_bytes: bytes) -> list:
        """
        解析温度数据字节
        
        Args:
            data_bytes: 60字节的温度数据
            
        Returns:
            30个浮点数的温度列表
        """
        temperatures = []
        
        for i in range(0, 60, 2):
            high_byte = data_bytes[i]
            low_byte = data_bytes[i + 1]
            raw_value = (high_byte << 8) | low_byte
            temp = raw_value / 10.0
            temperatures.append(temp)
        
        return temperatures
    
    def process_byte(self, byte: int) -> tuple:
        """
        状态机处理单个字节
        
        Args:
            byte: 接收到的字节值 (0-255)
            
        Returns:
            (success_flag, json_data): 成功返回 (True, 解析结果字典)，否则返回 (False, None)
        """
        result = (False, None)
        
        if self.state == ParserState.WAIT_FOR_HEADER_D:
            if byte == ord('D'):
                self.state = ParserState.WAIT_FOR_HEADER_A
                self.frame_buffer = bytearray([byte])
        
        elif self.state == ParserState.WAIT_FOR_HEADER_A:
            if byte == ord('A'):
                self.state = ParserState.WAIT_FOR_HEADER_T
                self.frame_buffer.append(byte)
            else:
                self.reset_state()
        
        elif self.state == ParserState.WAIT_FOR_HEADER_T:
            if byte == ord('T'):
                self.state = ParserState.WAIT_FOR_BOXID
                self.frame_buffer.append(byte)
            else:
                self.reset_state()
        
        elif self.state == ParserState.WAIT_FOR_BOXID:
            self.temp_boxid = byte
            self.state = ParserState.WAIT_FOR_SEQ
            self.frame_buffer.append(byte)
        
        elif self.state == ParserState.WAIT_FOR_SEQ:
            self.temp_seq = byte
            self.state = ParserState.WAIT_FOR_LENGTH
            self.frame_buffer.append(byte)
        
        elif self.state == ParserState.WAIT_FOR_LENGTH:
            self.temp_length = byte
            if self.temp_length == 0x3C:
                self.state = ParserState.WAIT_FOR_DATA
                self.frame_buffer.append(byte)
                self.data_bytes_remaining = 60
            else:
                self.reset_state()
        
        elif self.state == ParserState.WAIT_FOR_DATA:
            self.frame_buffer.append(byte)
            self.data_bytes_remaining -= 1
            if self.data_bytes_remaining == 0:
                self.state = ParserState.WAIT_FOR_CRC_HIGH
        
        elif self.state == ParserState.WAIT_FOR_CRC_HIGH:
            self.temp_crc_high = byte
            self.state = ParserState.WAIT_FOR_CRC_LOW
        
        elif self.state == ParserState.WAIT_FOR_CRC_LOW:
            received_crc = (self.temp_crc_high << 8) | byte
            calculated_crc = self.crc16_modbus(bytes(self.frame_buffer))
            
            if received_crc == calculated_crc:
                self.state = ParserState.WAIT_FOR_FOOTER_CR
            else:
                self.reset_state()
        
        elif self.state == ParserState.WAIT_FOR_FOOTER_CR:
            if byte == 0x0D:
                self.state = ParserState.WAIT_FOR_FOOTER_LF
            else:
                self.reset_state()
        
        elif self.state == ParserState.WAIT_FOR_FOOTER_LF:
            if byte == 0x0A:
                data_bytes = self.frame_buffer[6:66]
                temperatures = self.parse_temperature_data(data_bytes)
                
                result = {
                    "BoxID": self.temp_boxid,
                    "Seq": self.temp_seq,
                    "Temperatures": temperatures,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                }
                result = (True, result)
            
            self.reset_state()
        
        return result


def scan_serial_ports() -> list:
    """
    扫描系统上所有可用的串口
    
    Returns:
        可用串口列表，每个元素包含 (port, description, hwid)
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description, port.hwid) for port in ports]


def read_from_serial(port_name: str, baudrate: int = 9600, timeout: int = 1):
    """
    从指定串口读取数据并解析
    
    Args:
        port_name: 串口名称 (如 'COM1' 或 '/dev/ttyUSB0')
        baudrate: 波特率，默认 9600
        timeout: 读取超时时间（秒），默认 1秒
        
    Yields:
        (success_flag, data): 每次解析成功或失败时产生结果
    """
    parser = LoRaTemperatureParser()
    
    try:
        with serial.Serial(port_name, baudrate, timeout=timeout) as ser:
            print(f"已连接到串口: {port_name}, 波特率: {baudrate}")
            
            while True:
                try:
                    byte = ser.read(1)
                    if byte:
                        success, data = parser.process_byte(byte[0])
                        
                        if success:
                            yield (True, data)
                        else:
                            pass
                    else:
                        time.sleep(0.01)
                        
                except serial.SerialException as e:
                    yield (False, {"error": "SERIAL_ERROR", "message": f"串口通信错误: {str(e)}"})
                    break
                    
    except serial.SerialException as e:
        yield (False, {"error": "SERIAL_OPEN_FAILED", "message": f"无法打开串口 {port_name}: {str(e)}"})


def create_test_frame(box_id: int = 1, seq: int = 0, temperatures: list = None) -> bytes:
    """
    创建测试用的数据帧（用于调试）
    
    Args:
        box_id: 采集箱序号
        seq: 帧序列号
        temperatures: 温度列表（最多30个，不足则补25.0）
        
    Returns:
        完整的70字节数据帧
    """
    frame = bytearray()
    
    frame.extend(b'DAT')
    frame.append(box_id & 0xFF)
    frame.append(seq & 0xFF)
    frame.append(0x3C)
    
    if temperatures is None:
        temperatures = [25.0 + i * 0.5 for i in range(30)]
    else:
        while len(temperatures) < 30:
            temperatures.append(25.0)
    
    for temp in temperatures[:30]:
        raw = int(temp * 10)
        high_byte = (raw >> 8) & 0xFF
        low_byte = raw & 0xFF
        frame.append(high_byte)
        frame.append(low_byte)
    
    crc = LoRaTemperatureParser.crc16_modbus(bytes(frame))
    crc_high = (crc >> 8) & 0xFF
    crc_low = crc & 0xFF
    frame.append(crc_high)
    frame.append(crc_low)
    
    frame.append(0x0D)
    frame.append(0x0A)
    
    return bytes(frame)


def test_parser():
    """测试解析器功能"""
    print("=" * 60)
    print("LoRa 温度数据帧解析器测试")
    print("=" * 60)
    
    test_temperatures = [20.0, 21.5, 22.3, 23.7, 24.1]
    test_frame = create_test_frame(box_id=5, seq=123, temperatures=test_temperatures)
    
    print(f"\n测试帧原始数据 (十六进制):")
    print(' '.join(f'{b:02X}' for b in test_frame))
    
    parser = LoRaTemperatureParser()
    
    print(f"\n开始逐字节解析测试帧...")
    for i, byte in enumerate(test_frame):
        success, data = parser.process_byte(byte)
        
        if success:
            print(f"\n✓ 解析成功！")
            print(f"  BoxID: {data['BoxID']}")
            print(f"  Seq: {data['Seq']}")
            print(f"  温度数量: {len(data['Temperatures'])}")
            print(f"  前5个温度: {data['Temperatures'][:5]}")
            print(f"  时间戳: {data['Timestamp']}")
            print(f"\n  JSON 格式输出:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return (True, data)
    
    print("✗ 解析失败，未检测到完整帧")
    return (False, None)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LoRa 温度数据帧解析器')
    parser.add_argument('--port', '-p', type=str, help='串口名称 (如 COM3 或 /dev/ttyUSB0)')
    parser.add_argument('--baudrate', '-b', type=int, default=9600, help='波特率 (默认: 9600)')
    parser.add_argument('--test', '-t', action='store_true', help='运行测试模式')
    parser.add_argument('--scan', '-s', action='store_true', help='扫描可用串口')
    
    args = parser.parse_args()
    
    if args.scan:
        print("扫描可用串口...")
        ports = scan_serial_ports()
        if ports:
            print(f"\n发现 {len(ports)} 个串口:")
            for i, (port, desc, hwid) in enumerate(ports, 1):
                print(f"  {i}. {port}: {desc}")
                print(f"     HWID: {hwid}")
        else:
            print("未发现可用串口")
        return
    
    if args.test:
        test_parser()
        return
    
    if args.port:
        print(f"开始从串口 {args.port} 读取数据...")
        print("按 Ctrl+C 停止\n")
        
        try:
            for success, data in read_from_serial(args.port, args.baudrate):
                if success:
                    print(f"\n[成功] 收到数据帧:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(f"\n[错误] {data['error']}: {data['message']}")
                    
        except KeyboardInterrupt:
            print("\n\n用户停止程序")
    else:
        parser.print_help()
        print("\n示例用法:")
        print("  python lora_temperature_parser.py --scan          # 扫描串口")
        print("  python lora_temperature_parser.py --test          # 运行测试")
        print("  python lora_temperature_parser.py -p COM3 -b 9600  # 读取 COM3 串口")


if __name__ == "__main__":
    main()
