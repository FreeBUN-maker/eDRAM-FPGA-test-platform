## Why

现有 `src/vivado/config.json` 还是空对象，Vivado Tcl 流程缺少生成时序约束和引脚约束所需的项目、器件、顶层端口和板卡管脚信息。现在 RTL 顶层 `edram_pl_top.sv` 已经稳定，需要把 AXU5EVB-E 开发板手册中的 PL 端资源整理成可被 Tcl 脚本消费的配置文件。

## What Changes

- 补全 `src/vivado/config.json`，描述 Vivado 工程的目标器件 `xczu5ev-sfvc784-1-i`、顶层模块和 RTL 源文件列表。
- 为 `edram_pl_top.sv` 的外部端口提供约束配置，包括 PL 时钟、低有效复位、UART RX/TX、eDRAM 控制信号、地址/组选择、写数据和读数据端口。
- 在配置中记录时钟周期、I/O standard、管脚方向、总线位宽和端口到物理引脚的映射，使 Tcl 可以生成 XDC 中的 `create_clock` 与 `PACKAGE_PIN`/`IOSTANDARD` 约束。
- 明确无法从手册或 RTL 确认的管脚必须以待确认状态呈现，不允许 Tcl 静默生成错误的最终约束。

## Non-goals

- 不修改 UART 协议、eDRAM 控制时序或 RTL 模块行为。
- 不实现新的 Vivado Tcl 解析器；本变更只定义并填充其输入配置文件。
- 不引入 PS 端 block design、AXI 配置、软件启动流程或 Linux 驱动。
- 不验证外接 eDRAM 板的电气完整性、线序转接板或实际示波器时序。

## Capabilities

### New Capabilities

- `vivado-config-json`: 定义 Vivado 配置 JSON 必须包含的项目元数据、源文件、时钟约束、端口约束、管脚映射和待确认项处理规则。

### Modified Capabilities

- None.

## Impact

- Affected config: `src/vivado/config.json`.
- Affected future flow: Vivado Tcl 脚本可基于该 JSON 生成工程、时钟 XDC 和引脚 XDC。
- Affected references: `prompt.md`、`src/rtl/edram_pl_top.sv`、`FPGA-instruction/AXU5EVB-E开发板用户手册.pdf`。
- Dependencies: 需要从板卡手册或后续用户确认中获得每个外部端口的最终 PL package pin。
