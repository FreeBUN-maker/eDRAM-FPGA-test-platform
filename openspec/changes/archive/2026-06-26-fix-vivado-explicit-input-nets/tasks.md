## 1. Failure Reproduction and Audit

- [x] 1.1 Record the Tcl console root cause from the Windows Vivado run in the implementation notes
- [x] 1.2 Audit `src/rtl/*.sv` for module input ports declared without an explicit net type under ``default_nettype none``
- [x] 1.3 Confirm `src/vivado/sources.tcl` still resolves file objects one source at a time

## 2. RTL Declaration Fixes

- [x] 2.1 Update scalar and vector `input logic` module ports to explicit `input wire logic` declarations
- [x] 2.2 Update package-typed module inputs such as `input edram_req_e` to explicit `input wire edram_req_e` declarations
- [x] 2.3 Verify no module port names, directions, widths, parameters, or instance connections changed

## 3. Vivado Source Helper Safeguards

- [x] 3.1 Preserve required-source existence checks in `edram_vivado::add_rtl_sources`
- [x] 3.2 Preserve per-file `get_files` object lookup to avoid Vivado `Too many positional options` errors
- [x] 3.3 Ensure Windows-style absolute paths remain supported when the project-mode Tcl script is run from the GUI

## 4. Validation

- [x] 4.1 Add or run a static check that fails on module input ports relying on implicit net types
- [x] 4.2 Run available local HDL tests or lint checks in the project environment
- [x] 4.3 Run `src/vivado/run_project_mode.tcl` in Windows Vivado and confirm xsim compile advances past the reported `cmd_dispatcher.sv` VRFC errors
- [x] 4.4 If Vivado is unavailable locally, document the exact command and expected Tcl console checkpoints for the Windows rerun

## Implementation Notes

- 2026-06-26: Windows Vivado 2019.1 reached xsim compile/analyze, then stopped at `[VRFC 10-1103] net type must be explicitly specified ... when default_nettype is none`, first reported for `src/rtl/cmd_dispatcher.sv:6`.
- 2026-06-26: Audited RTL module port lists and found module input declarations using `input logic` plus one package-typed `input edram_req_e`; function/task arguments were excluded from the module-port fix.
- 2026-06-26: Confirmed `src/vivado/sources.tcl` retains `assert_files_exist`, resolves source paths with `file normalize`, and queries file objects one source at a time in `get_file_objects`.
- 2026-06-26: Updated RTL module input ports to `input wire logic` and the package-typed controller request input to `input wire edram_req_e`; `git diff` shows declaration-only edits in module port lists.
- 2026-06-26: Added and ran `scripts/check_vivado_explicit_input_nets.py`; it checked 11 SystemVerilog files and passed.
- 2026-06-26: `conda run -n track4-fa python sim/tb/run_cocotb.py` passed with Verilator/cocotb.
- 2026-06-26: `tclsh` validate-only run passed with `::EDRAM_VIVADO_VALIDATE_ONLY=1`.
- 2026-06-26: `command -v vivado` did not find Vivado in this Linux workspace; Windows Vivado rerun command and expected checkpoints were documented in `doc/Vivado-project-mode-flow.md`.
- 2026-06-26: User manually reran the project-mode Tcl flow in Windows Vivado and confirmed xsim no longer stops at the previous `cmd_dispatcher.sv` VRFC net-type error.
