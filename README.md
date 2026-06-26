# FPGA eDRAM测试平台
本项目用于构建基于FPGA的eDRAM测试平台，平台的基本功能定义如下：
- 该平台可以同时与PC端、eDRAM器件电路板进行连接
- 该平台可以通过串口接收PC端发来的指令，并根据指令输出eDRAM器件的控制信号；可以通过串口将eDRAM器件的读出结果发送回PC端进行结果验证
- 该平台能够根据`doc/eDRAM-interface.md`文件中定义的eDRAM接口，正确地输出控制信号来控制eDRAM进行写入、读出操作
- FPGA搭建只用开发板的PL端，降低工程复杂度
- 可以对写信号进行自检操作，要求可以实现FPGA上输出的信号能够直接从输出端口处引出，并通过uart接口发回PC端接受检查

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

# Vivado工程构建
- Vivado GUI project mode 构建入口为 `src/vivado/run_project_mode.tcl`，可通过 `Tools -> Run Tcl Script` 执行。
- 默认流程会创建工程、加入 RTL、加载 `src/vivado/edram_pl_board.xdc`、运行 Vivado xsim smoke 仿真、综合、实现并生成 bitstream。
- 详细用法见 `doc/Vivado-project-mode-flow.md`。

# 主机端UART通信测试
- Python脚本入口为 `scripts/uart_host_test.py`，协议frame构造和解析 helper 为 `scripts/uart_host_protocol.py`。
- 硬件串口访问依赖 `pyserial`。在项目环境中安装：

```bash
conda activate track4-fa
python -m pip install pyserial
```

- 不连接FPGA时，可以先运行协议frame自测试：

```bash
python scripts/uart_host_protocol.py
```

- 查找主机串口：

```bash
python scripts/uart_host_test.py list
```

  Linux常见端口名为 `/dev/ttyUSB0` 或 `/dev/ttyACM0`；Windows常见端口名为 `COM7` 这类 `COMx`。Linux若无权限访问串口，通常需要把当前用户加入 `dialout` 组或临时调整设备权限。

`basic` 和 `smoke` 等价，`full` 和 `memtest` 等价；推荐日常使用 `basic` 与 `full` 这两个名字。

## 基础模式
基础模式只测试 `RESET`、`PING`、`STATUS`，用于确认 `PC -> UART interface -> FPGA dispatcher -> UART interface -> PC` 的基本双向链路，不依赖eDRAM阵列读写结果。

```bash
python scripts/uart_host_test.py basic --port /dev/ttyUSB0
python scripts/uart_host_test.py basic --port COM7
```

也可以单独运行：

```bash
python scripts/uart_host_test.py ping --port /dev/ttyUSB0 --count 10
python scripts/uart_host_test.py status --port /dev/ttyUSB0
```

调试原始收发字节时加 `--verbose`：

```bash
python scripts/uart_host_test.py basic --port /dev/ttyUSB0 --verbose
```

基础模式通过时会看到 `RESET: PASS`、`PING: PASS`、`STATUS: PASS` 和 `BASIC: PASS`。

## 完整模式
完整模式会测试UART ISA中当前定义的所有指令：`RESET`、`PING`、`STATUS`、`WRITE_ROW`、`READ_GROUP`、`READ_ROW`。它会写入指定scratch row，再用 `READ_GROUP` 逐组读回，并用 `READ_ROW` 读取整行比较，因此只应在eDRAM板已连接且该行允许被覆盖时运行。

```bash
python scripts/uart_host_test.py full --port /dev/ttyUSB0 --row 0 --pattern walking
python scripts/uart_host_test.py full --port COM7 --row 0 --data "00 11 22 33 44 55 66 77"
```

可用 `--pattern` 包括 `doc`、`walking`、`checker`、`inverse-checker`、`increment`、`zero`、`ones`。`--data` 可以传入8个显式byte，例如 `"00 11 22 33 44 55 66 77"` 或 `0011223344556677`。

完整模式通过时会看到 `WRITE_ROW: PASS`、`READ_GROUP: PASS groups=0..7`、`READ_ROW: PASS` 和 `FULL: PASS`。

常见失败含义：
- `timed out`：串口端口、波特率、板卡供电、bitstream或UART管脚连接可能不正确。
- `FPGA returned NACK_*`：FPGA收到了frame但拒绝执行，可根据状态码检查长度、checksum、参数范围、busy或FSM timeout。
- `payload mismatch`：`PING`或其他命令响应payload与协议不一致。
- `READ_GROUP mismatch` 或 `READ_ROW mismatch`：UART命令通路已返回响应，但eDRAM写读数据不一致，需要继续检查eDRAM连接、时序参数或被测row。
