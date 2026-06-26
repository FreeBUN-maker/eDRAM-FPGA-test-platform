## Context

本项目要构建一个基于 FPGA PL 端的 eDRAM 测试平台。PC 通过 UART 发送事务级命令，FPGA 在 PL 逻辑中完成 frame 接收、校验、指令解析、eDRAM 控制时序生成和读出结果返回。现有文档已经定义：

- 项目只使用开发板 PL 端，降低工程复杂度。
- UART 默认物理层为 `115200-8-N-1`。
- PC 发送完整 frame，FPGA 校验后执行事务，不允许 PC 逐拍控制底层 eDRAM 信号。
- eDRAM 阵列规模为 `64 x 64`，地址由 `ROW[5:0]` 和 `GROUP[2:0]` 组成。
- eDRAM 控制信号 `LOAD`、`READ`、`EN-WWL`、`EN-RWL` 均为低有效，空闲值为 `1`。

整体设计只依赖 PL 端时钟、复位、UART RX/TX 管脚和 eDRAM 管脚。Zynq PS 端、AXI 总线、ARM 软件和 Linux 驱动均不参与基础读写路径。

### Block diagram

```text
 PC host
 Python/serial
     |
     | UART 115200-8-N-1
     v
+----------------------- FPGA PL -----------------------+
|                                                       |
|  +----------+    +-----------+    +----------------+  |
|  | baud gen |--->| uart_rx   |--->| frame_parser   |  |
|  +----------+    +-----------+    +----------------+  |
|                                            | cmd_valid |
|                                            v           |
|  +----------+    +-----------+    +----------------+  |
|  | uart_tx  |<---| resp_enc  |<---| cmd_dispatcher |  |
|  +----------+    +-----------+    +----------------+  |
|                                            | ctrl_req  |
|                                            v           |
|                                  +----------------+   |
|                                  | edram_ctrl_fsm |   |
|                                  +----------------+   |
|                                     |          ^       |
|                                     v          |       |
|                                eDRAM pins   P[7:0]    |
+-------------------------------------------------------+
```

## Goals / Non-Goals

**Goals:**

- Define a PL-only RTL architecture that can be implemented in SystemVerilog and synthesized in Vivado.
- Define module boundaries and ready/valid style handshakes between UART, parser, dispatcher, response encoder, and eDRAM controller.
- Execute the existing UART protocol commands: `PING`, `WRITE_ROW`, `READ_GROUP`, `READ_ROW`, `RESET`, and `STATUS`.
- Generate deterministic eDRAM write/read timing with parameterized setup, pulse, sample, recovery, and timeout cycle counts.
- Keep all eDRAM output pins in documented idle values during reset, parser errors, checksum errors, invalid arguments, and controller timeout recovery.

**Non-Goals:**

- Add PS-side control, AXI register access, DMA, interrupt handling, or embedded software.
- Redefine the UART frame format or opcode assignment.
- Guarantee burst throughput or tolerate arbitrary host-side streaming without waiting for responses.
- Finalize board XDC pin names or external analog/electrical timing values; those are supplied by board constraints and later measurement.

## Decisions

### Decision: Use a PL-only top-level with no PS dependency

The top-level module exposes only clock/reset, UART pins, and eDRAM pins:

```text
clk_i
rst_ni
uart_rx_i
uart_tx_o
edram_load_n_o
edram_read_n_o
edram_en_wwl_n_o
edram_en_rwl_n_o
edram_wg_o[2:0]
edram_rg_o[2:0]
edram_din_o[7:0]
edram_a_o[5:0]
edram_w_o[5:0]
edram_p_i[7:0]
```

Rationale: the project goal explicitly prefers PL-only implementation. A self-contained top-level also makes the design easier to simulate because the testbench can directly drive UART and observe eDRAM pins.

Alternative considered: expose a PS/AXI register bank and let software sequence commands. That would simplify some debug flows, but it adds Vivado block design, PS boot, address mapping, and software dependencies that are not needed for the first bring-up.

### Decision: Use byte-stream modules around a transaction dispatcher

The UART side is split into:

- `uart_baud_gen`: derives baud ticks from `CLK_HZ` and `UART_BAUD`.
- `uart_rx`: converts serial RX into `rx_byte`, `rx_valid`, and framing-error status.
- `uart_frame_parser`: waits for `SOF=0x55`, collects `LEN`, `OP`, `ARGS`, verifies XOR checksum, and emits one parsed request.
- `uart_resp_encoder`: builds `[0xAA] [LEN] [STATUS] [OP_ECHO] [DATA...] [CHK]`.
- `uart_tx`: serializes response bytes.

The parser stores at most one request frame at a time. The v1 host flow control rule is request/response: PC sends the next request only after receiving the previous response. If a valid request arrives while the eDRAM controller is busy, `cmd_dispatcher` returns `NACK_BUSY` and does not start a new transaction.

Alternative considered: a wider streaming FIFO and pipelined command queue. It improves back-to-back throughput, but hides protocol mistakes during bring-up and complicates busy/error behavior. The first revision favors one visible transaction at a time.

### Decision: Centralize opcode validation in `cmd_dispatcher`

`cmd_dispatcher` receives parsed frames and owns the command contract:

| OP | Command | Dispatcher behavior |
| --- | --- | --- |
| `0x00` | `PING` | Return ACK payload `0xA5` without touching eDRAM pins. |
| `0x01` | `WRITE_ROW` | Validate one row plus eight data bytes, then issue one write-row request to `edram_ctrl_fsm`. |
| `0x02` | `READ_GROUP` | Validate row/group, issue one read-group request, return one data byte. |
| `0x03` | `READ_ROW` | Validate row, issue eight read-group requests for groups `0..7`, return eight data bytes. |
| `0x04` | `RESET` | Soft-reset parser-visible status and force eDRAM controller idle, then return ACK. |
| `0x05` | `STATUS` | Return `[STATE] [LAST_ERR]`. |

Invalid length, bad checksum, unsupported opcode, out-of-range row/group, busy, and timeout map to the existing NACK status codes.

Alternative considered: let the eDRAM controller interpret opcodes directly. Keeping the low-level controller command-neutral makes the eDRAM FSM easier to test with direct micro-operations.

### Decision: Keep eDRAM control in a dedicated parameterized FSM

The controller accepts two micro-operations:

```text
WRITE_ROW(row[5:0], data[0..7])
READ_GROUP(row[5:0], group[2:0]) -> data[7:0]
```

Timing constants are compile-time parameters in clock cycles:

```text
T_LOAD_SETUP_CYCLES
T_LOAD_PULSE_CYCLES
T_LOAD_RECOVER_CYCLES
T_WWL_SETUP_CYCLES
T_WWL_PULSE_CYCLES
T_WWL_RECOVER_CYCLES
T_READ_SETUP_CYCLES
T_RWL_PULSE_CYCLES
T_READ_SAMPLE_CYCLES
T_READ_RECOVER_CYCLES
CTRL_TIMEOUT_CYCLES
```

The initial defaults may be conservative single-digit cycle counts for simulation, but the names make it straightforward to tune after board-level measurement or eDRAM characterization. Every parameter used as a wait count must be constrained to at least one cycle in RTL.

Alternative considered: hard-code one-cycle pulses. That is convenient for unit tests but too brittle for an external eDRAM device whose setup, hold, and read stabilization time may need adjustment.

### Decision: Pulse `LOAD` once per write group

Although the interface document describes enabling `LOAD` while scanning `WG`, the RTL should use a conservative per-group load pulse:

1. Set `WG=group` and `DIN=data[group]` while `LOAD=1`.
2. Wait `T_LOAD_SETUP_CYCLES`.
3. Assert `LOAD=0` for `T_LOAD_PULSE_CYCLES`.
4. Deassert `LOAD=1` and wait `T_LOAD_RECOVER_CYCLES`.
5. Continue with the next group.

Rationale: this avoids writing during `WG` or `DIN` transitions and makes setup/hold timing explicit. After all eight groups are loaded, the controller commits the row by asserting `EN-WWL=0` with `A=row` stable.

Alternative considered: keep `LOAD=0` throughout all eight group selections. That is shorter, but it risks unintended buffer writes if `WG` or `DIN` glitches during transitions.

### Write timing diagram

Signals use `_n` suffix for active-low RTL names. Values shown are logical pin values.

```text
phase        idle   setup g0  load g0  recover  ... setup g7 load g7 recover  row setup  commit   idle
WG[2:0]      000    000       000      000           111      111     111      111        111      000
DIN[7:0]     00     D0        D0       D0            D7       D7      D7       D7         D7       00
LOAD_n       1      1         0        1             1        0       1        1          1        1
A[5:0]       00     00        00       00            00       00      00       ROW        ROW      00
EN_WWL_n     1      1         1        1             1        1       1        1          0        1
READ_n       1      1         1        1             1        1       1        1          1        1
EN_RWL_n     1      1         1        1             1        1       1        1          1        1
```

The write transaction completes only after `EN_WWL_n` has returned high and `T_WWL_RECOVER_CYCLES` has elapsed.

### Decision: Sample read data after address and enable settle windows

For a group read:

1. Keep write controls idle: `LOAD=1`, `EN-WWL=1`.
2. Set `W=row` and `RG=group`.
3. Assert `READ=0` and wait `T_READ_SETUP_CYCLES`.
4. Assert `EN-RWL=0`.
5. Wait `T_READ_SAMPLE_CYCLES`, then sample `P[7:0]`.
6. Keep `EN-RWL=0` until `T_RWL_PULSE_CYCLES` is satisfied if the sample point is earlier than the full pulse width.
7. Deassert `EN-RWL=1`, then `READ=1`, wait `T_READ_RECOVER_CYCLES`, and return data.

`P[7:0]` is an external, FPGA-controlled asynchronous input. The RTL should register it before use, with an optional two-stage synchronizer controlled by a parameter such as `P_SYNC_STAGES`. The sample point must be after the configured settle window.

Alternative considered: sample `P[7:0]` on the same cycle that `EN-RWL` is asserted. That is not safe because the eDRAM read bitlines need time to settle.

### Read timing diagram

```text
phase        idle   addr setup/read setup   rwl active/sample    recover     idle
W[5:0]       00     ROW                     ROW                  ROW         00
RG[2:0]      000    GROUP                   GROUP                GROUP       000
READ_n       1      0                       0                    0/1         1
EN_RWL_n     1      1                       0                    1           1
P[7:0]       x      settling                stable -> sampled    x           x
LOAD_n       1      1                       1                    1           1
EN_WWL_n     1      1                       1                    1           1
```

`READ_ROW` is implemented by the dispatcher as eight serialized `READ_GROUP` micro-operations. The response payload order is `GROUP=0` through `GROUP=7`.

### Decision: Fail closed on errors and timeouts

Bad checksum and malformed requests must not start eDRAM transactions. Controller timeout forces all eDRAM outputs to idle values, records `LAST_ERR=NACK_TIMEOUT`, and returns a timeout response when possible. Synchronous reset and UART `RESET` both drive the eDRAM interface to idle; UART `RESET` additionally clears parser-visible status such as `LAST_ERR`.

Alternative considered: leave pins in their last state for debug visibility. That can damage test validity by unintentionally holding an active-low eDRAM enable, so idle recovery is the safer default.

## Risks / Trade-offs

- eDRAM exact setup/hold requirements are not fully documented -> Use parameterized timing constants and tune them during board bring-up.
- Per-group `LOAD` pulses make writes slower than holding `LOAD` low through all groups -> The UART link is already slow compared with the PL clock, so correctness is more valuable than saving a few PL cycles.
- One in-flight request limits throughput -> The initial protocol is simpler and easier to debug; burst commands can be added after basic correctness is verified.
- `P[7:0]` has no source-synchronous clock -> Sample only after `T_READ_SAMPLE_CYCLES` and optionally pass through synchronizer registers.
- Active-low signal names are easy to misuse -> RTL should use `_n` suffix internally and testbenches should assert idle values after every reset, error, and transaction.

## Migration Plan

1. Add `src/rtl` modules for UART baud generation, RX, TX, frame parser, response encoder, command dispatcher, eDRAM controller, and PL top-level integration.
2. Add `sim/tb` testbenches that instantiate the PL top or submodules and drive byte-level UART frames.
3. Verify parser and response behavior against `doc/FPGA-PC-UART-interface.md`.
4. Verify eDRAM write/read signal timing with assertions or cycle-count checks.
5. Add Vivado project/Tcl wiring and XDC constraints after the logical pin list is stable.

Rollback is simple before RTL integration because this change only adds design/spec artifacts. After RTL exists, rollback means disabling the new PL top-level from the Vivado file list.

## Open Questions

- What PL input clock frequency should be the default for AXU5EVB-E in this project, such as `100 MHz` or another board clock?
- What conservative initial values should be used for each eDRAM timing parameter before board measurement?
- Should `READ` be asserted before address setup to exactly mirror the current prose document, or should the final RTL keep address stable first and only require `EN-RWL` after address setup? This design chooses the latter for glitch avoidance.
- Does the eDRAM board require external level shifting or pin-drive constraints beyond standard 3.3 V LVCMOS settings?

## Modules to be revised

- `src/rtl/edram_pl_top.sv`
- `src/rtl/uart_baud_gen.sv`
- `src/rtl/uart_rx.sv`
- `src/rtl/uart_tx.sv`
- `src/rtl/uart_frame_parser.sv`
- `src/rtl/uart_resp_encoder.sv`
- `src/rtl/cmd_dispatcher.sv`
- `src/rtl/edram_ctrl_fsm.sv`
- `sim/tb/*_tb.sv`
- `src/vivado/*.tcl`
- `doc/eDRAM-FPGA-interface.md` if later documentation needs to align wording with the selected glitch-avoidance timing.
