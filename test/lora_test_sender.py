#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoRa 温度数据帧测试发送端
用于模拟 LoRa 采集终端发送数据，验证 lora_temperature_parser.py 的解析逻辑
"""

import serial
import serial.tools.list_ports
import random
import time
from datetime import datetime
import json


def crc16_modbus(data: bytes) -> int:
    """
    CRC-16/MODBUS 校验算法（与接收端保持一致）
    
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


def generate_random_temperatures(min_temp: float = -10.0, max_temp: float = 60.0) -> list:
    """
    随机生成 30 路温度数值
    
    Args:
        min_temp: 最小温度值
        max_temp: 最大温度值
        
    Returns:
        30个浮点数的温度列表
    """
    temperatures = []
    for _ in range(30):
        temp = round(random.uniform(min_temp, max_temp), 1)
        temperatures.append(temp)
    return temperatures


def create_frame(box_id: int, seq: int, temperatures: list, corrupt_crc: bool = False, corrupt_header: bool = False) -> bytes:
    """
    创建数据帧
    
    协议格式（70字节）：
    - Header (3 Bytes): 'D', 'A', 'T' (ASCII)
    - BoxID (1 Byte): 采集箱序号
    - Seq (1 Byte): 帧序列号 (0-255)
    - Length (1 Byte): 负载长度，固定为 0x3C (60)
    - Data (60 Bytes): 30路温度数据，每路2字节（高八位在前）
    - CRC16 (2 Bytes): CRC-16/MODBUS 校验（校验范围：字节0到65）
    - Footer (2 Bytes): 0x0D, 0x0A (\r\n)
    
    Args:
        box_id: 采集箱序号
        seq: 帧序列号
        temperatures: 30路温度列表
        corrupt_crc: 是否故意损坏 CRC（用于测试异常）
        corrupt_header: 是否故意损坏帧头（用于测试异常）
        
    Returns:
        完整的70字节数据帧
    """
    frame = bytearray()
    
    if corrupt_header:
        frame.extend(b'XAT')
    else:
        frame.extend(b'DAT')
    
    frame.append(box_id & 0xFF)
    frame.append(seq & 0xFF)
    frame.append(0x3C)
    
    for temp in temperatures[:30]:
        raw = int(temp * 10)
        high_byte = (raw >> 8) & 0xFF
        low_byte = raw & 0xFF
        frame.append(high_byte)
        frame.append(low_byte)
    
    crc = crc16_modbus(bytes(frame))
    
    if corrupt_crc:
        crc = (crc + 1) & 0xFFFF
    
    crc_high = (crc >> 8) & 0xFF
    crc_low = crc & 0xFF
    frame.append(crc_high)
    frame.append(crc_low)
    
    frame.append(0x0D)
    frame.append(0x0A)
    
    return bytes(frame)


def scan_serial_ports() -> list:
    """
    扫描系统上所有可用的串口
    
    Returns:
        可用串口列表
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description, port.hwid) for port in ports]


def print_frame_hex(frame: bytes, description: str = ""):
    """
    打印帧的十六进制表示
    
    Args:
        frame: 数据帧字节
        description: 描述信息
    """
    if description:
        print(f"\n{description}")
    
    hex_str = ' '.join(f'{b:02X}' for b in frame)
    print(f"原始数据 (十六进制, 共{len(frame)}字节):")
    print(hex_str)
    
    print("\n帧结构解析:")
    print(f"  Header (0-2):  {frame[0]:02X} {frame[1]:02X} {frame[2]:02X}  ({chr(frame[0])}{chr(frame[1])}{chr(frame[2])})")
    print(f"  BoxID (3):     {frame[3]:02X}  ({frame[3]})")
    print(f"  Seq (4):       {frame[4]:02X}  ({frame[4]})")
    print(f"  Length (5):    {frame[5]:02X}  ({frame[5]}字节)")
    print(f"  Data (6-65):   {frame[6]:02X} {frame[7]:02X} ... {frame[64]:02X} {frame[65]:02X}  (60字节)")
    print(f"  CRC (66-67):   {frame[66]:02X} {frame[67]:02X}")
    print(f"  Footer (68-69):{frame[68]:02X} {frame[69]:02X}  (\\r\\n)")


def send_test_frames(port_name: str, baudrate: int = 9600, interval: int = 2, 
                      box_id: int = 1, send_errors: bool = False,
                      random_boxes: bool = False, box_range: list = None):
    """
    通过串口发送测试帧
    
    Args:
        port_name: 串口名称
        baudrate: 波特率
        interval: 发送间隔（秒）
        box_id: 采集箱ID（当 random_boxes 为 False 时使用）
        send_errors: 是否发送错误帧（用于测试）
        random_boxes: 是否随机选择多个采集箱
        box_range: 随机选择的采集箱范围（如 [1, 2, 3, 4]）
    """
    # 每个采集箱独立的序列号
    seqs: Dict[int, int] = {}
    frame_count = 0
    error_frame_count = 0
    
    # 初始化采集箱序列号
    if random_boxes:
        if box_range is None:
            box_range = [1, 2, 3, 4]  # 默认使用所有4个采集箱
        for bid in box_range:
            seqs[bid] = 0
    else:
        seqs[box_id] = 0
        box_range = [box_id]
    
    try:
        with serial.Serial(port_name, baudrate, timeout=1) as ser:
            print("=" * 70)
            print("LoRa 温度数据帧测试发送端")
            print("=" * 70)
            print(f"串口: {port_name}")
            print(f"波特率: {baudrate}")
            print(f"发送间隔: {interval}秒")
            if random_boxes:
                print(f"随机采集箱模式: 是 (范围: {box_range})")
            else:
                print(f"采集箱ID: {box_id}")
            print(f"发送错误帧: {'是' if send_errors else '否'}")
            print("=" * 70)
            print("\n[使用说明]")
            print("  1. 请在另一个终端运行接收端: python lora_temperature_parser.py -p <配对串口>")
            print("  2. 发送端会打印原始随机温度列表，接收端会输出解析后的JSON")
            print("  3. 请手动比对发送端的温度列表和接收端输出的 Temperatures 是否一致")
            print("  4. 按 Ctrl+C 停止发送\n")
            
            print("=" * 70)
            print("开始发送数据帧...")
            print("=" * 70)
            
            while True:
                # 随机选择采集箱（如果启用了随机模式）
                if random_boxes:
                    current_box_id = random.choice(box_range)
                else:
                    current_box_id = box_id
                
                # 获取当前采集箱的序列号
                current_seq = seqs[current_box_id]
                
                # 生成随机温度
                temperatures = generate_random_temperatures()
                frame_type = "正常帧"
                is_error_frame = False
                
                # 决定是否发送错误帧
                if send_errors and frame_count > 0 and frame_count % 5 == 0:
                    error_type = random.choice(['crc', 'header'])
                    if error_type == 'crc':
                        frame = create_frame(current_box_id, current_seq, temperatures, corrupt_crc=True)
                        frame_type = "错误帧 (CRC损坏)"
                    else:
                        frame = create_frame(current_box_id, current_seq, temperatures, corrupt_header=True)
                        frame_type = "错误帧 (帧头损坏)"
                    is_error_frame = True
                    error_frame_count += 1
                else:
                    frame = create_frame(current_box_id, current_seq, temperatures)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                print(f"\n{'='*70}")
                print(f"[{timestamp}] 发送第 {frame_count + 1} 帧 - {frame_type}")
                print(f"{'='*70}")
                
                print(f"\n[发送端原始数据]")
                print(f"  BoxID: {current_box_id}")
                print(f"  Seq: {current_seq}")
                print(f"\n  随机温度列表 (30路):")
                
                for i in range(0, 30, 5):
                    temp_slice = temperatures[i:i+5]
                    temp_str = "  "
                    for j, temp in enumerate(temp_slice):
                        idx = i + j
                        temp_str += f"T{idx+1:2d}:{temp:5.1f}°C  "
                    print(temp_str)
                
                print_frame_hex(frame, f"\n[数据帧详情]")
                
                ser.write(frame)
                ser.flush()
                
                print(f"\n[验证提示]")
                if is_error_frame:
                    print(f"  ⚠  这是一个错误帧，接收端应该丢弃此帧并输出错误标志")
                    print(f"     (CRC错误或帧头错误会导致解析失败)")
                else:
                    print(f"  ✓ 请检查接收端输出的 JSON:")
                    print(f"    - BoxID 应该为: {current_box_id}")
                    print(f"    - Seq 应该为: {current_seq}")
                    print(f"    - Temperatures 应该与上面的 30 路温度列表一致")
                    print(f"    - 如果不一致，说明解析逻辑有问题！")
                
                # 更新序列号（每个采集箱独立）
                seqs[current_box_id] = (current_seq + 1) & 0xFF
                frame_count += 1
                
                print(f"\n等待 {interval} 秒后发送下一帧...")
                time.sleep(interval)
                
    except serial.SerialException as e:
        print(f"\n[错误] 串口操作失败: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print("用户停止发送")
        print(f"{'='*70}")
        print(f"\n发送统计:")
        print(f"  总帧数: {frame_count}")
        print(f"  正常帧: {frame_count - error_frame_count}")
        print(f"  错误帧: {error_frame_count}")
        print(f"\n各采集箱序列号状态:")
        for bid, seq in seqs.items():
            print(f"  采集箱 {bid}: Seq = {seq}")
        return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LoRa 温度数据帧测试发送端')
    parser.add_argument('--port', '-p', type=str, help='串口名称 (如 COM1 或 /dev/pts/1)')
    parser.add_argument('--baudrate', '-b', type=int, default=9600, help='波特率 (默认: 9600)')
    parser.add_argument('--interval', '-i', type=int, default=2, help='发送间隔（秒，默认: 2）')
    parser.add_argument('--boxid', type=int, default=1, help='采集箱ID (默认: 1)')
    parser.add_argument('--errors', '-e', action='store_true', help='发送错误帧（用于测试异常处理）')
    parser.add_argument('--random', '-r', action='store_true', help='随机选择多个采集箱 (默认: 1-4)')
    parser.add_argument('--box-range', type=str, default='1,2,3,4', help='随机选择的采集箱范围 (如 1,2,3,4)')
    parser.add_argument('--scan', '-s', action='store_true', help='扫描可用串口')
    parser.add_argument('--test', '-t', action='store_true', help='运行本地测试（不使用串口）')
    
    args = parser.parse_args()
    
    # 解析采集箱范围
    box_range = None
    if args.random:
        try:
            box_range = [int(x.strip()) for x in args.box_range.split(',')]
            # 过滤有效的采集箱ID (1-4)
            box_range = [x for x in box_range if 1 <= x <= 4]
            if not box_range:
                box_range = [1, 2, 3, 4]
        except ValueError:
            print(f"警告: 无效的采集箱范围 '{args.box_range}'，使用默认值 [1, 2, 3, 4]")
            box_range = [1, 2, 3, 4]
    
    if args.scan:
        print("扫描可用串口...")
        ports = scan_serial_ports()
        if ports:
            print(f"\n发现 {len(ports)} 个串口:")
            for i, (port, desc, hwid) in enumerate(ports, 1):
                print(f"  {i}. {port}: {desc}")
        else:
            print("未发现可用串口")
        return
    
    if args.test:
        print("=" * 70)
        print("本地测试模式（验证帧生成逻辑）")
        print("=" * 70)
        
        temperatures = generate_random_temperatures()
        print(f"\n生成的随机温度列表:")
        for i in range(0, 30, 5):
            print(f"  {temperatures[i:i+5]}")
        
        normal_frame = create_frame(box_id=5, seq=123, temperatures=temperatures)
        print_frame_hex(normal_frame, "\n正常帧:")
        
        bad_crc_frame = create_frame(box_id=5, seq=123, temperatures=temperatures, corrupt_crc=True)
        print_frame_hex(bad_crc_frame, "\nCRC损坏帧:")
        
        bad_header_frame = create_frame(box_id=5, seq=123, temperatures=temperatures, corrupt_header=True)
        print_frame_hex(bad_header_frame, "\n帧头损坏帧:")
        
        print("\n" + "=" * 70)
        print("本地测试完成")
        print("=" * 70)
        print("\n联调测试步骤:")
        print("  1. 使用 VSPD 或 socat 创建虚拟串口对（如 COM1 <-> COM2）")
        print("  2. 终端1（发送端）: python lora_test_sender.py -p COM1 -i 2")
        print("  3. 终端2（接收端）: python lora_temperature_parser.py -p COM2")
        print("  4. 比对发送端打印的温度列表和接收端输出的 JSON")
        print("\n多箱随机测试:")
        print("  python lora_test_sender.py -p COM1 -i 2 -r          # 随机发送 1-4 号采集箱")
        print("  python lora_test_sender.py -p COM1 -i 2 -r --box-range 1,3  # 随机发送 1 和 3 号采集箱")
        return
    
    if args.port:
        send_test_frames(
            port_name=args.port,
            baudrate=args.baudrate,
            interval=args.interval,
            box_id=args.boxid,
            send_errors=args.errors,
            random_boxes=args.random,
            box_range=box_range
        )
    else:
        parser.print_help()
        print("\n示例用法:")
        print("  python lora_test_sender.py --scan                    # 扫描串口")
        print("  python lora_test_sender.py --test                    # 本地测试")
        print("  python lora_test_sender.py -p COM1 -i 2             # 发送到 COM1，每2秒一帧")
        print("  python lora_test_sender.py -p COM1 -i 2 -e          # 同时发送错误帧测试")
        print("  python lora_test_sender.py -p COM1 -i 2 -r          # 随机发送多个采集箱 (1-4)")
        print("  python lora_test_sender.py -p COM1 -i 2 -r --box-range 1,3  # 随机发送 1 和 3 号采集箱")


if __name__ == "__main__":
    main()
