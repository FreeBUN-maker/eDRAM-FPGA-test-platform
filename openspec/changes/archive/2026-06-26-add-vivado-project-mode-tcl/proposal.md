## Why

当前仓库已经包含板级 RTL、`src/vivado/config.json`、`src/vivado/sources.tcl` 和 `src/vivado/edram_pl_board.xdc`，但还缺少一个可以在 Vivado GUI 中通过 `Tools -> Run Tcl Script` 直接执行的 project mode 构建入口。新增该入口可以让板级工程创建、约束加载、仿真、综合、实现和比特流生成形成可重复流程，减少手动 GUI 操作导致的配置漂移。

## What Changes

- 新增 Vivado project mode Tcl 脚本，作为 GUI `Run Tcl Script` 和 Tcl console 均可执行的主入口。
- 脚本基于现有 `src/vivado/config.json`、`src/vivado/sources.tcl` 和 `src/vivado/edram_pl_board.xdc` 创建 Vivado project，设置目标器件、顶层、默认库、SystemVerilog 源文件和约束文件。
- 脚本提供可配置的构建阶段，支持项目创建、约束定义、仿真准备/运行、综合、实现和比特流生成。
- 脚本在关键阶段进行存在性检查和失败即停处理，并输出明确日志，便于从 Vivado GUI 消息窗口定位失败原因。
- 保留现有 RTL、约束和 JSON 语义，不改动 UART 协议、eDRAM 控制时序或板级端口定义。

## Non-goals

- 不引入 Vivado block design、PS/AXI 集成、软件工程或 Vitis 流程。
- 不替代现有 cocotb/Verilator 单元测试流程；Vivado 仿真只覆盖 Vivado project mode 可直接运行的仿真入口。
- 不重新生成或重新确认板卡引脚映射；脚本应消费现有 XDC/JSON，不在本变更中改变管脚选择。
- 不保证在未安装 Vivado、缺少仿真 testbench 或缺少有效许可的环境中完成实际综合/实现。

## Capabilities

### New Capabilities

- `vivado-project-mode-tcl`: 定义 Vivado project mode Tcl 脚本的可执行入口、配置消费、工程创建、约束加载、仿真、综合、实现、比特流生成和错误处理要求。

### Modified Capabilities

- None.

## Impact

- Affected scripts: `src/vivado/` 下新增 project mode Tcl 主脚本，并复用 `src/vivado/sources.tcl`。
- Affected configuration: 读取现有 `src/vivado/config.json` 中的项目名、目标器件、顶层和源文件元数据。
- Affected constraints: 将 `src/vivado/edram_pl_board.xdc` 加入 Vivado constrs fileset。
- Affected verification/build flow: Vivado GUI 用户可通过 `Tools -> Run Tcl Script` 触发项目构建、仿真、综合、实现和 bitstream 生成。
