## Why

现有文档已经定义了 eDRAM 测试平台的基本目标、UART 事务协议和 eDRAM 侧接口信号，但还缺少一个只使用 PL 端实现的 FPGA 设计方案。该方案需要把 PC 侧 UART frame 转换为可仿真、可综合、时序可控的 eDRAM 读写控制事务，为后续 RTL 实现和 testbench 编写提供统一依据。

## What Changes

- 定义一个 PL-only FPGA 顶层设计，不依赖 Zynq PS 端软件或 AXI 控制路径。
- 细化 UART RX/TX、frame 解析、命令分发、响应生成和 eDRAM 控制状态机之间的模块边界与握手机制。
- 定义 UART 指令解析模块如何执行 `PING`、`WRITE_ROW`、`READ_GROUP`、`READ_ROW`、`RESET`、`STATUS` 等事务级命令。
- 定义 eDRAM 控制接口的空闲值、写入时序、读出时序、读数据采样点和超时/恢复行为。
- 定义仿真验证范围，包括 UART frame 解析、错误处理、完整行写入、单组读取、整行读取和控制信号时序检查。

## Non-goals

- 不定义新的 PC-to-FPGA UART 协议格式；本变更沿用 `doc/FPGA-PC-UART-interface.md` 和既有 `define-uart-protocol` 变更中的事务语义。
- 不实现 PS 端软件、AXI-Lite 寄存器映射、Linux 驱动或 ARM 侧调试路径。
- 不锁定最终 PCB 引脚约束或电平转换电路细节；本变更只规定 RTL 可见的逻辑接口和时序行为。
- 不追求高吞吐 burst 读写，优先保证基础读写事务正确。

## Capabilities

### New Capabilities

- `pl-only-control-plane`: 定义只使用 FPGA PL 端的顶层模块、UART 收发与指令解析、命令执行握手、响应生成、复位和状态管理。
- `edram-control-timing`: 定义 eDRAM 控制接口的空闲状态、写入/读出状态机、参数化等待周期、读数据采样和异常恢复要求。

### Modified Capabilities

- None.

## Impact

- Affected RTL: future `src/rtl` modules for UART RX/TX, frame parser, command dispatcher, response encoder, eDRAM controller, and top-level integration.
- Affected simulation: future `sim/tb` testbenches for parser behavior, command execution, response frames, and eDRAM control timing.
- Affected docs: future design documentation may reference this OpenSpec design as the implementation plan for the PL-only platform.
- Dependencies: SystemVerilog and Vivado flow only; no new PS-side dependency is introduced.
