# FPGA eDRAM测试平台
本项目用于构建基于FPGA的eDRAM测试平台，平台的基本功能定义如下：
- 该平台可以同时与PC端、eDRAM器件电路板进行连接
- 该平台可以通过串口接收PC端发来的指令，并根据指令输出eDRAM器件的控制信号；可以通过串口将eDRAM器件的读出结果发送回PC端进行结果验证
- 该平台能够根据`doc/eDRAM-interface.md`文件中定义的eDRAM接口，正确地输出控制信号来控制eDRAM进行写入、读出操作
- FPGA搭建只用开发板的PL端，降低工程复杂度

# 文件结构
- doc: 存放功能描述、使用方法等项目文档
- src: 存放rtl设计文件以及控制vivado配置的tcl脚本
- sim: 存放用于测试的代码文件
- FPGA-instruction: 存放FPGA的使用说明书

# RTL顶层与时钟
- `src/rtl/edram_pl_top.sv` 是可复用核心逻辑顶层，仍使用单端 `clk_i`，便于仿真和非板级集成。
- AXU5EVB-E 板级 Vivado 工程使用 `src/rtl/edram_pl_board_top.sv` 作为 top。该 wrapper 接收 `PL_CLK0_P/PL_CLK0_N` 200 MHz 差分时钟，并通过 `pl_clk_diff_to_single` 生成单端核心时钟。
- 默认 MMCM 参数为 200 MHz 输入、100 MHz 输出；需要调整核心时钟频率时，修改 board top 的时钟参数并同步更新 `src/vivado/config.json` 中的 `CLK_HZ`。
- 默认参数对应 `200 MHz * 5 / 1 = 1 GHz` VCO、`1 GHz / 10 = 100 MHz` 输出；该组合已按 AMD DS925 的 Zynq UltraScale+ MMCM switching range 做过初步检查，最终板级约束仍以 Vivado DRC/Timing 为准。
