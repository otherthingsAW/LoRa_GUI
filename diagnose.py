#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本：检查导入和初始化问题
"""

import sys
import os

print("=" * 60)
print("诊断信息")
print("=" * 60)

print(f"\n1. Python版本: {sys.version}")
print(f"2. 工作目录: {os.getcwd()}")
print(f"3. 脚本位置: {os.path.abspath(__file__)}")

# 检查 src 目录是否存在
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
print(f"4. src目录路径: {src_dir}")
print(f"   是否存在: {os.path.exists(src_dir)}")

# 检查 sys.path
print(f"\n5. sys.path:")
for p in sys.path:
    print(f"   - {p}")

# 尝试导入模块
print("\n" + "=" * 60)
print("尝试导入模块")
print("=" * 60)

# 添加项目根目录到 sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"\n已添加项目根目录到 sys.path: {project_root}")

# 检查是否可以导入
try:
    print("\n尝试导入 src.lora_temperature_parser...")
    import src.lora_temperature_parser
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n尝试导入 src.producer...")
    import src.producer
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n尝试导入 src.consumer...")
    import src.consumer
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n尝试导入 src.state_manager...")
    import src.state_manager
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n尝试导入 src.ui...")
    import src.ui
    print("   ✓ 成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 尝试实际使用模块
print("\n" + "=" * 60)
print("尝试创建组件")
print("=" * 60)

try:
    from src.state_manager import StateManager
    from pathlib import Path
    
    config_path = Path(__file__).parent / 'multi_box_config.json'
    print(f"\n创建 StateManager...")
    print(f"配置文件: {config_path}")
    print(f"是否存在: {config_path.exists()}")
    state_manager = StateManager(str(config_path))
    print("   ✓ StateManager 创建成功")
except Exception as e:
    print(f"   ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n诊断完成")
