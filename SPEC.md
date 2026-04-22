# 混凝土温度监控系统技术规格书 (SPEC)

## 1. 项目基本信息
- **项目名称**：Concrete-Temp-Monitor
- **开发语言**：Python 3.8+
- **核心框架**：NiceGUI (Frontend), PySerial (Communication)
- **底层解析器**：`lora_temperature_parser.py`
- **应用场景**：大体积混凝土施工现场，多节点无线温度监控。

---

## 2. 系统架构设计

系统采用 **生产者-消费者 (Producer-Consumer)** 异步模式，以确保高并发串口数据读取与 UI 响应的解耦。

### 2.1 数据流向
1. **数据源**：LoRa 采集箱通过串口发送二进制字节流。
2. **生产者 (Producer)**：由 `LoRaProducer` 类驱动，维护 `pyserial` 连接，并调用解析逻辑。
3. **数据转换**：将二进制帧解析为标准字典对象。
4. **分发器**：生产者遍历 `consumers` 列表，将数据字典分发给所有注册的消费者。
5. **消费者 (Consumers)**：
    - **UI 消费者**：更新 NiceGUI 响应式状态。
    - **存储消费者**：执行 CSV 持久化操作。

---

## 3. 接口规范 (Interface Specification)

### 3.1 解析器输出接口 (Parser Output)
根据 `lora_temperature_parser.py` 的定义，单条解析完成的数据对象必须符合以下格式：

```json
{
    "BoxID": "1",                    // 采集箱唯一标识 (str: "1"-"4")
    "Seq": 128,                      // 循环帧序列号 (int: 0-255)
    "Temperatures": [25.1, ...],     // 30个通道的温度浮点数 (list[float])
    "Timestamp": "2026-04-22 19:05:01.123" // 数据生成时间戳
}
```
### 3.2 消费者类标准
所有消费者类必须实现 consume(data: dict) 方法。

# 4. 功能模块详述
## 4.1 前端 UI 模块 (NiceGUI)
- 混凝土温度看板：使用 ui.grid 展示 30 个通道。
- 动态备注绑定：
    - UI 需根据当前数据的 BoxID 动态从 all_remarks 字典中检索并显示测点名称。- 卡片颜色/边框需具备工业感（推荐绿色系 #2e7d32）。
- 设备配置面板：
    - 提供串口号动态扫描下拉框。
    - 提供波特率选择下拉框。
    - 备注管理系统：4 个采集箱独立的备注编辑表单，支持实时修改并持久化至 multi_box_config.json。

## 4.2 后端持久化模块 (Storage)
- 分箱存储策略：每一路 BoxID 对应一个独立的 CSV 文件，命名规则为 concrete_log_box_{id}_{time}.csv。
- 表头动态化：CSV 首次创建时，提取当前 all_remarks 中的配置作为表头。
- 编码标准：采用 utf-8-sig 编码，确保在 Microsoft Excel 中直接打开不乱码。
- 滚动更新数据：单个文件不超过1000条，超过1000条另外创建新的csv文件。
- 存储在Documents目录下的LoRa_Log文件夹中。
# 5. 异常处理与性能
## 5.1 串口容错
- 热插拔支持：串口连接丢失后，系统进入 5 秒周期的静默重连模式。
- 参数动态更新：用户修改串口配置后，系统应立即断开旧连接并根据新参数建立连接。
## 5.2 解析鲁棒性
- Header 寻址：必须通过 buffer.find(b'DAT') 寻找帧起始，以应对数据偏移。
- 校验机制：必须通过 CRC-16/MODBUS 校验，非法包直接丢弃，不分发给消费者。