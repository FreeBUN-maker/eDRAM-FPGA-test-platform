# Vivado Project Mode Flow

本流程用于从 Vivado GUI 直接创建并运行 eDRAM FPGA 测试平台的 project mode 构建。

## GUI 用法

1. 打开 Vivado。
2. 选择 `Tools -> Run Tcl Script`。
3. 选择仓库中的 `src/vivado/run_project_mode.tcl`。

默认执行完整流程：

```text
project -> sources -> constraints -> simulate -> synth -> impl -> bitstream
```

默认生成目录：

```text
build/vivado/edram_fpga_test_platform/
```

默认 bitstream 位置：

```text
build/vivado/edram_fpga_test_platform/edram_fpga_test_platform.runs/impl_1/edram_pl_board_top.bit
```

## 输入文件

脚本从自身路径自动定位仓库根目录，并使用以下文件：

- `src/vivado/config.json`: project 名称、器件型号、顶层模块、默认库和语言配置。
- `src/vivado/sources.tcl`: RTL 源文件顺序和 Vivado add/read helper。
- `src/vivado/edram_pl_board.xdc`: AXU5EVB-E 板级管脚和时钟约束。
- `sim/tb/edram_pl_board_top_vivado_tb.sv`: Vivado xsim smoke testbench。

`config.json` 中的 `target_language` 为 `SystemVerilog` 时，脚本会将 Vivado project 的 `target_language` 映射为 `Verilog`，RTL 文件类型仍按 SystemVerilog 加入工程。

## Tcl Console 用法

可以在 Vivado Tcl Console 中预设全局变量后再 source 脚本：

```tcl
set ::EDRAM_VIVADO_STAGES {project sources constraints simulate}
set ::EDRAM_VIVADO_RECREATE 0
set ::EDRAM_VIVADO_JOBS 8
source /absolute/path/to/src/vivado/run_project_mode.tcl
```

支持的 stage 名称：

```text
project sources constraints simulate synth impl bitstream
```

`all` 或不设置 stage 时运行完整流程。

## 环境变量用法

同名环境变量也可用于 batch 或 shell 启动：

```bash
export EDRAM_VIVADO_STAGES="project,sources,constraints,synth,impl,bitstream"
export EDRAM_VIVADO_RECREATE=1
export EDRAM_VIVADO_JOBS=8
vivado -mode batch -source src/vivado/run_project_mode.tcl
```

可选变量：

- `EDRAM_VIVADO_STAGES`: 要执行的 stage 列表，逗号或空格分隔。
- `EDRAM_VIVADO_PROJECT_DIR`: 覆盖生成 project 目录；相对路径按仓库根目录解析。
- `EDRAM_VIVADO_RECREATE`: `1` 时删除并重建生成 project 目录，`0` 时打开已有 `.xpr` 或创建新工程。
- `EDRAM_VIVADO_JOBS`: Vivado run 并行 job 数，默认 `4`。
- `EDRAM_VIVADO_VALIDATE_ONLY`: `1` 时只做 Tcl/路径/config 静态检查，不调用 Vivado project 命令。

## 非 Vivado 静态检查

没有 Vivado 时可以用系统 `tclsh` 做基础检查：

```bash
tclsh <<'EOF'
set ::EDRAM_VIVADO_VALIDATE_ONLY 1
source src/vivado/run_project_mode.tcl
EOF
```

该检查会验证 Tcl 可解析、必需文件存在、`config.json` 的 project 字段可读取、stage override 可解析；不会执行 xsim、综合、实现或 bitstream 生成。

## Windows Vivado 复测检查点

在 Windows Vivado Tcl Console 中可直接复测默认完整流程：

```tcl
source E:/Files/Li_Meng/eDRAM/FPGA/src/vivado/run_project_mode.tcl
```

如果只想复测到 xsim 编译和 smoke simulation，可先限制 stage：

```tcl
set ::EDRAM_VIVADO_STAGES {project sources constraints simulate}
source E:/Files/Li_Meng/eDRAM/FPGA/src/vivado/run_project_mode.tcl
```

预期 Tcl Console 检查点：

- 出现 `Configured sources_1 top: edram_pl_board_top`。
- 出现 `Configured sim_1 top: edram_pl_board_top_vivado_tb`。
- xsim 进入 `XSim::Compile design` 和 `COMPILE and ANALYZE`。
- 不再出现 `[VRFC 10-1103] net type must be explicitly specified`，尤其不应再停在 `cmd_dispatcher.sv:6`。
- smoke simulation 结束后出现 `Vivado simulation completed`，且不再出现 `Simulation failed: wrong # args: should be "run"`。
- 默认完整流程随后继续 synthesis、implementation 和 bitstream；只运行到 `simulate` stage 时则应在仿真完成后正常结束。
