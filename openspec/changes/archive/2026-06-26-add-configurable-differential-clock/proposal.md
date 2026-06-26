## Why

当前 RTL 核心以单端 `clk_i` 作为时钟输入，但 AXU5EVB-E 的 PL 侧板载用户时钟是 200 MHz 差分对 `PL_CLK0_P/PL_CLK0_N`。Vivado 配置已将该时钟标记为 unresolved，因此需要补上一个板级差分时钟前端，把差分输入转换为可供现有 RTL 使用的单端全局时钟。

## What Changes

- 新增一个参数化差分时钟转单端时钟模块，用于接收板载 200 MHz 差分输入并输出单端 PL 逻辑时钟。
- 通过参数配置 MMCM/PLL 的倍频、分频和输出频率元数据，使单端输出时钟频率可在综合参数中调整。
- 新增或调整板级顶层 wrapper，暴露 `pl_clk0_p_i`/`pl_clk0_n_i` 差分端口，实例化时钟模块，并将输出时钟连接到现有 `edram_pl_top.clk_i`。
- 更新 Vivado 配置中的顶层、源文件、时钟端口和差分时钟管脚信息，解除当前 `clk_i` 单端端口与板载差分时钟不匹配的问题。
- 增加针对时钟模块参数合法性、wrapper 连接关系和 Vivado 配置一致性的验证。

## Non-goals

- 不重写 UART 协议、eDRAM 控制 FSM 或现有 transaction 数据路径。
- 不把现有 `edram_pl_top` 改成依赖 Xilinx 时钟原语的仿真顶层；现有核心 RTL 仍保持单端 `clk_i` 输入。
- 不引入 PS 端 block design、AXI clocking wizard、软件启动流程或 Linux 驱动。
- 不自动搜索所有可能的 MMCM 参数组合；本变更定义可配置参数与合法性检查，具体频率由参数组合决定。

## Capabilities

### New Capabilities

- `configurable-differential-clock`: 定义板级差分时钟输入、参数化 MMCM/PLL 分频配置、单端全局时钟输出、lock/reset 行为，以及 Vivado 配置对差分时钟端口的约束要求。

### Modified Capabilities

- None.

## Impact

- Affected RTL: 新增 `src/rtl/pl_clk_diff_to_single.sv` 和板级 wrapper，如 `src/rtl/edram_pl_board_top.sv`。
- Affected existing RTL: `src/rtl/edram_pl_top.sv` 继续作为核心逻辑顶层，内部仍使用 `clk_i`。
- Affected config: `src/vivado/config.json` 需要加入新 RTL 源文件、板级 top、`PL_CLK0_P/PL_CLK0_N` 差分时钟端口和输出时钟参数。
- Affected tests: cocotb/Verilator 需要覆盖参数计算、非综合仿真旁路和 wrapper 对 `edram_pl_top` 的连接。
- Dependencies: Xilinx Vivado 综合路径使用 FPGA 原语 `IBUFDS`、MMCM/PLL 和 `BUFG`。
