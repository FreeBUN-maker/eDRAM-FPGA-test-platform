## 1. Input Discovery

- [x] 1.1 Inspect `src/rtl/edram_pl_top.sv` and record every external scalar and bus port with direction and width
- [x] 1.2 Inspect `src/rtl` and produce the ordered SystemVerilog source list required by `edram_pl_top`
- [x] 1.3 Review `FPGA-instruction/AXU5EVB-E开发板用户手册.pdf` for the target part, PL clock source, reset/UART options, and candidate expansion connector package pins
- [x] 1.4 Identify which `edram_pl_top` ports have confirmed board package pins and which remain unresolved

## 2. Config JSON Implementation

- [x] 2.1 Populate `src/vivado/config.json` with project metadata including name, part `xczu5ev-sfvc784-1-i`, top `edram_pl_top`, and default library
- [x] 2.2 Add the ordered RTL source list to `src/vivado/config.json`
- [x] 2.3 Add the `clk_i` clock constraint object with clock name, frequency, period, I/O standard, package pin state, and provenance
- [x] 2.4 Add scalar port constraint entries for reset, UART, and active-low eDRAM control signals
- [x] 2.5 Add bit-ordered bus constraint entries for eDRAM group, data, row, and readback buses
- [x] 2.6 Add structured unresolved entries for every required pin mapping that cannot be confirmed

## 3. Validation

- [x] 3.1 Validate that `src/vivado/config.json` parses as strict JSON
- [x] 3.2 Validate that the JSON port entries match `edram_pl_top.sv` port names, directions, and widths
- [x] 3.3 Validate that `edram_pkg.sv` appears before dependent RTL sources in the configured source list
- [x] 3.4 Validate that unresolved required pins are reported clearly before final pin XDC generation
- [x] 3.5 Run the available Vivado Tcl dry-run, JSON validation script, or a documented fallback command and record the result

## Implementation Notes

- 2026-06-26: `python -m json.tool src/vivado/config.json` passed.
- 2026-06-26: Python fallback validation confirmed 14 configured ports match `src/rtl/edram_pl_top.sv` names, directions, and widths.
- 2026-06-26: Python fallback validation confirmed `src/rtl/edram_pkg.sv` is first in the configured source list and every configured RTL source exists.
- 2026-06-26: Python fallback validation reported one required unresolved pin: `clk_i`, because the AXU5EVB-E manual provides a differential `PL_CLK0_P/N` source while the current RTL top exposes only single-ended `clk_i`.
