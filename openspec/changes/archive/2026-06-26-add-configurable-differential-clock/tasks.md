## 1. Clock Module RTL

- [x] 1.1 Add `src/rtl/pl_clk_diff_to_single.sv` with differential clock inputs, `clk_o`, `locked_o`, reset input, and frequency-control parameters
- [x] 1.2 Implement the synthesis clock path with `IBUFDS`, MMCM/PLL primitive parameters, feedback buffering, and output `BUFG`
- [x] 1.3 Add parameter-derived frequency validation so `OUTPUT_CLK_HZ` matches the MMCM multiply/divide formula within an explicit tolerance
- [x] 1.4 Add a Verilator/cocotb-friendly simulation bypass path that drives `clk_o` deterministically and asserts `locked_o` after reset release

## 2. Board-Level Integration

- [x] 2.1 Add `src/rtl/edram_pl_board_top.sv` exposing `pl_clk0_p_i`, `pl_clk0_n_i`, reset, UART, and all existing eDRAM external ports
- [x] 2.2 Instantiate `pl_clk_diff_to_single` in the board wrapper with a 200 MHz input-clock default and a documented default output frequency
- [x] 2.3 Add reset gating and synchronized reset release so `edram_pl_top.rst_ni` stays low until the clock generator is locked
- [x] 2.4 Instantiate `edram_pl_top` from the board wrapper and pass the generated `OUTPUT_CLK_HZ` value to `CLK_HZ`
- [x] 2.5 Keep `edram_pl_top.sv` functionally unchanged unless a minimal parameter plumbing change is required

## 3. Vivado Configuration

- [x] 3.1 Update `src/vivado/config.json` project metadata so the Vivado top is the board-level wrapper
- [x] 3.2 Add the new clock module and board wrapper to the ordered RTL source list
- [x] 3.3 Replace the unresolved single-ended `clk_i` clock entry with differential `pl_clk0_p_i` and `pl_clk0_n_i` clock-port metadata
- [x] 3.4 Record AXU5EVB-E clock pins `AE5` and `AF5`, the 200 MHz input frequency, and the generated output clock frequency parameters
- [x] 3.5 Remove or resolve the existing `clk_i` unresolved entry so final pin XDC generation no longer treats the clock as incomplete

## 4. Verification

- [x] 4.1 Add a focused test for `pl_clk_diff_to_single` simulation bypass, lock behavior, and parameter consistency checks
- [x] 4.2 Add a board-wrapper test that drives complementary differential clock inputs and verifies reset remains asserted until lock
- [x] 4.3 Verify `edram_pl_board_top` connects the generated clock and synchronized reset into `edram_pl_top`
- [x] 4.4 Run the existing cocotb suite to confirm direct `edram_pl_top` tests still pass
- [x] 4.5 Run JSON validation or a lightweight port/config consistency check for the updated Vivado configuration

## 5. Review

- [x] 5.1 Review default MMCM parameters against UltraScale+ legal VCO and output divider ranges before treating the configuration as board-ready
- [x] 5.2 Update any local documentation that describes the top-level clock port so it points board builds at `edram_pl_board_top`
