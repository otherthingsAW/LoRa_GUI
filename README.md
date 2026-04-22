# 混凝土温度监控系统 (LoRa 4箱版)

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-orange.svg)
![Protocol](https://img.shields.io/badge/Protocol-LoRa-green.svg)

本系统是一款专为大体积混凝土施工设计的温度实时监控软件。通过 LoRa 无线通信接收 4 个采集箱（每箱 30 通道）的数据，提供直观的 Web 界面展示及自动化的 CSV 存证功能。

## 🌟 功能特性

- **多箱独立管理**：支持 4 个采集箱 (BoxID 1-4) 同时工作，每个箱子拥有独立的 30 通道备注设置。
- **动态 UI 切换**：界面能够根据当前接收到的数据包自动切换对应箱子的备注信息，实现“所见即所得”。
- **工业级解析**：内置 CRC-16/MODBUS 校验，采用滑动窗口算法处理 LoRa 传输中的断帧与杂质字节。
- **实时配置**：支持在网页端动态扫描串口、修改波特率，无需重启程序即可应用新连接。
- **自动化存储**：按箱号自动分档存储 CSV 文件，支持 `UTF-8-SIG` 编码，确保 Excel 打开中文备注不乱码。
- **数据持久化**：通道备注信息自动保存至本地 JSON 文件，程序重启后配置依然保留。

## 🛠️ 技术栈

- **前端/后端**：[NiceGUI](https://nicegui.io/) (基于 FastAPI & Vue)
- **通信**：PySerial (异步串口读写)
- **校验**：Crcmod (Modbus 算法)
- **数据格式**：二进制字节流 (Little/Big Endian 混合处理)

## 📦 安装与启动

### 1. 克隆或下载本项目
确保你已安装 Python 3.8 或更高版本。

### 2. 安装依赖
在终端/命令行中运行以下命令安装必要库：

```bash
pip install nicegui pyserial crcmod
