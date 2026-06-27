## Context

现有核心顶层 `src/rtl/edram_pl_top.sv` 只有单端 `clk_i` 输入，并把 `CLK_HZ` 参数传递给 UART RX/TX 的 baud 计数逻辑。AXU5EVB-E 板卡 PL 端提供的是 200 MHz 差分时钟 `PL_CLK0_P/PL_CLK0_N`，当前 `src/vivado/config.json` 已将 `clk_i` 标记为 unresolved，因为单端顶层端口无法直接绑定这对差分管脚。

本设计在板级边界新增差分时钟适配层，保持核心 eDRAM/UART RTL 继续使用单端 `clk_i`。这样既能满足板卡实现需要，也能保留现有 `edram_pl_top` cocotb 测试的简单输入时钟模型。

### Block diagram

```text
+----------------------- AXU5EVB-E PL board top -----------------------+
|                                                                      |
|  PL_CLK0_P ----+                                                     |
|                |                                                     |
|             +---------------------------+                            |
|  PL_CLK0_N ->| pl_clk_diff_to_single    |-- core_clk_i               |
|             | - IBUFDS                  |                            |
| rst_ni ---->| - MMCM/PLL params         |-- clk_locked               |
|             | - BUFG                    |                            |
|             +---------------------------+                            |
|                            |                                         |
|                            v                                         |
|                    +----------------+                                |
|                    | reset sync     |-- core_rst_ni                  |
|                    +----------------+                                |
|                            |                                         |
|                            v                                         |
|                    +----------------+                                |
| UART/eDRAM pins <--| edram_pl_top   |                                |
|                    | .clk_i(core)   |                                |
|                    +----------------+                                |
+----------------------------------------------------------------------+
```

## Goals / Non-Goals

**Goals:**

- Convert the AXU5EVB-E 200 MHz differential PL clock into a single-ended global clock for the existing RTL.
- Keep `edram_pl_top` as the reusable core integration module with a single-ended `clk_i`.
- Provide synthesis parameters that control the generated clock frequency through MMCM/PLL multiply/divide values.
- Hold the core in reset until the generated clock is locked and reset release has been synchronized to the generated clock domain.
- Update Vivado configuration so the build top and clock constraints describe the differential board clock instead of unresolved `clk_i`.
- Preserve Verilator/cocotb usability with a simulation bypass or black-box strategy that does not require Xilinx primitive models.

**Non-Goals:**

- Do not redesign eDRAM command execution, UART protocol, or controller timing state machines.
- Do not implement a runtime-programmable clock generator; frequency selection is a build-time parameter choice.
- Do not create a Vivado Clocking Wizard IP project; the RTL should remain reviewable SystemVerilog around explicit Xilinx primitives.
- Do not guarantee a frequency from an arbitrary integer parameter alone; legal frequencies are limited by MMCM/PLL VCO and output divider ranges.

## Decisions

### Decision: Add a board-level wrapper instead of changing the core top

Create `edram_pl_board_top` as the Vivado top-level. It exposes the physical board clock ports:

```text
pl_clk0_p_i
pl_clk0_n_i
rst_ni
uart_rx_i
uart_tx_o
edram_* ports
```

The wrapper instantiates `pl_clk_diff_to_single`, reset synchronization, and the existing `edram_pl_top`. `edram_pl_top` continues to expose `clk_i`, so existing unit tests and any future non-board integrations can still drive a simple clock.

Alternative considered: replace `edram_pl_top.clk_i` with differential ports directly. That would solve pin binding, but it couples all existing simulation and reusable RTL to Xilinx clocking primitives.

### Decision: Use IBUFDS + MMCM + BUFG for the clock path

The synthesis implementation of `pl_clk_diff_to_single` uses:

- `IBUFDS` to receive `pl_clk0_p_i/pl_clk0_n_i`.
- `MMCME4_BASE` or an equivalent UltraScale+ MMCM primitive for configurable multiply/divide.
- `BUFG` on the generated clock before driving core logic.
- A lock output exported as `locked_o`.

The module parameters should mirror the primitive knobs:

```systemverilog
parameter int unsigned INPUT_CLK_HZ = 200_000_000;
parameter real CLKFBOUT_MULT_F = 5.000;
parameter int unsigned DIVCLK_DIVIDE = 1;
parameter real CLKOUT0_DIVIDE_F = 10.000;
parameter int unsigned OUTPUT_CLK_HZ = 100_000_000;
```

The generated frequency is:

```text
VCO_HZ    = INPUT_CLK_HZ * CLKFBOUT_MULT_F / DIVCLK_DIVIDE
clk_o Hz  = VCO_HZ / CLKOUT0_DIVIDE_F
```

`OUTPUT_CLK_HZ` is used as a machine-readable contract for downstream RTL parameters such as `edram_pl_top.CLK_HZ`, and simulation/validation should check it matches the MMCM formula within integer rounding tolerance.

Alternative considered: use a simple `IBUFDS` followed by `BUFG` and always run the core at 200 MHz. That is simpler, but it does not satisfy the requirement that output frequency be controllable by parameters.

### Decision: Keep frequency control explicit rather than auto-searching dividers

The first implementation should not try to search for legal MMCM settings from only a desired `OUTPUT_CLK_HZ`. Instead, the user sets legal primitive parameters and the module validates the resulting frequency. This makes synthesis behavior transparent and avoids hiding invalid VCO or divider combinations.

Example parameter choices:

```text
Input 200 MHz, mult 5, divclk 1, clkout divide 10 -> 100 MHz output
Input 200 MHz, mult 5, divclk 1, clkout divide 5  -> 200 MHz output
Input 200 MHz, mult 6, divclk 1, clkout divide 12 -> 100 MHz output
```

Alternative considered: generate a lookup table or compile-time search for MMCM settings. That can be added later, but it is more code and still needs device-specific legal range checks.

### Decision: Reset the core only after clock lock

The wrapper computes an asynchronous reset source from the external active-low reset and clock lock, then releases reset through a small synchronizer clocked by the generated clock:

```text
core_reset_async_n = rst_ni & clk_locked
core_rst_ni        = synchronized release in core_clk_i domain
```

This prevents the eDRAM controller and UART baud counters from leaving reset before the generated clock is stable.

### Timing diagram

```text
time              t0          t1              t2              t3
PL_CLK0_P/N       toggling    toggling        toggling        toggling
rst_ni            0           1               1               1
mmcm_locked       0           0               1               1
core_clk_i        invalid     settling        stable          stable
core_rst_ni       0           0               0               1
edram outputs     reset idle  reset idle      reset idle      functional
```

Reset deassertion at `t3` occurs only after `mmcm_locked` is high and the synchronizer has observed enough `core_clk_i` edges.

### Decision: Support simulation without Xilinx primitive models

`pl_clk_diff_to_single` should include a simulation path controlled by a parameter such as `SIM_BYPASS` and guarded for Verilator when necessary. In simulation bypass mode:

- `clk_o` follows `clk_p_i` or another simple driven test clock.
- `locked_o` asserts after reset deassertion.
- Parameter validation still runs so invalid frequency metadata is caught.

The synthesis path remains the Xilinx primitive implementation. This keeps the board wrapper testable while avoiding a dependency on vendor simulation libraries in the existing `conda activate track4-fa` flow.

### Modules to be revised

- Add `src/rtl/pl_clk_diff_to_single.sv`.
- Add `src/rtl/edram_pl_board_top.sv`.
- Keep `src/rtl/edram_pl_top.sv` functionally unchanged, but instantiate it from the board wrapper with `CLK_HZ` set to the generated output frequency.
- Update `src/vivado/config.json` so project top is the board wrapper, source list includes both new files, and the clock entry describes `pl_clk0_p_i/pl_clk0_n_i` with board pins `AE5/AF5`.
- Update `sim/tb/run_cocotb.py` or add a focused test runner entry for wrapper/clock-parameter validation if needed.

### Impact on the overall system

The UART baud generator and eDRAM timing parameters continue to count generated core clock cycles. Therefore changing the generated clock frequency requires keeping `CLK_HZ` and timing-cycle parameters consistent with the selected output clock. The board wrapper should pass the clock module's `OUTPUT_CLK_HZ` value to `edram_pl_top.CLK_HZ`, and `src/vivado/config.json` should record the same frequency for review.

## Risks / Trade-offs

- Invalid MMCM settings -> Validate input/output frequencies and document legal parameter sets; rely on Vivado DRC for final primitive legality.
- `OUTPUT_CLK_HZ` metadata diverges from MMCM parameters -> Add simulation-time assertions or validation scripts comparing the formula to the declared frequency.
- Reset released before stable clock -> Gate reset with `locked_o` and synchronize deassertion in the generated clock domain.
- Verilator cannot elaborate vendor primitives -> Provide a simulation bypass and keep primitive code out of the active Verilator branch.
- Existing Vivado config change is active in another OpenSpec change -> Keep this change's spec focused on the clock capability and implement config updates carefully against the current `src/vivado/config.json`.

## Migration Plan

1. Add the reusable clock module and board wrapper while leaving `edram_pl_top` unchanged.
2. Update Vivado configuration to use `edram_pl_board_top` as the synthesis top and to bind the differential clock pins.
3. Add or update tests for parameter validation, reset/lock behavior, and wrapper connectivity.
4. Run the existing cocotb suite with the core top still driven by a direct clock.
5. Run focused wrapper/clock tests in simulation bypass mode.
6. Roll back by restoring Vivado top to `edram_pl_top` and removing the new board wrapper/source entries if the board-level clock path blocks synthesis.

## Open Questions

- Which output frequency should be the project default for board bring-up: 100 MHz for conservative timing margin, or 200 MHz to match the board source?
- Should the final XDC use a confirmed differential I/O standard from the board manual, or should it remain marked for manual confirmation until the Vivado flow is generated?
