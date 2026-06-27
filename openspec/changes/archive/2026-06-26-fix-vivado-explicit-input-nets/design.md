## Context

The project-mode Tcl flow now reaches Vivado xsim after creating the project, adding RTL sources, adding the XDC, and configuring `sim_1`. The latest Tcl console failure occurs during `xvlog --incr --relax`, where Vivado 2019.1 VRFC reports `net type must be explicitly specified` for module input ports while ``default_nettype none`` is active.

The earlier console output also showed `get_files` receiving a multi-file list as positional arguments. The current source helper already addresses this by resolving and querying file objects one source at a time, so this change should preserve that behavior while fixing the next compile blocker.

Affected modules:

- `src/rtl/uart_baud_gen.sv`
- `src/rtl/uart_rx.sv`
- `src/rtl/uart_tx.sv`
- `src/rtl/uart_frame_parser.sv`
- `src/rtl/uart_resp_encoder.sv`
- `src/rtl/cmd_dispatcher.sv`
- `src/rtl/edram_ctrl_fsm.sv`
- `src/rtl/edram_pl_top.sv`
- `src/rtl/pl_clk_diff_to_single.sv`
- `src/rtl/edram_pl_board_top.sv`

System impact:

```text
Vivado GUI / Tcl Console
        |
        v
src/vivado/run_project_mode.tcl
        |
        v
src/vivado/sources.tcl  --->  sources_1 RTL files
        |                         |
        v                         v
sim_1 smoke testbench       Vivado VRFC/xsim compile
                                  |
                                  v
                      simulation -> synth -> impl -> bitstream
```

The change affects source compatibility at the compile boundary only; it does not alter the UART protocol, controller sequencing, clocking intent, or board pin constraints.

Timing of the failing flow and fixed flow:

```text
Current:
project -> sources -> constraints -> launch_simulation -> xvlog compile fails -> stop

After fix:
project -> sources -> constraints -> launch_simulation -> xvlog compile passes
                                                        -> run smoke sim
                                                        -> synth/impl/bitstream
```

## Goals / Non-Goals

**Goals:**

- Make Vivado 2019.1 xsim compile RTL modules while ``default_nettype none`` remains enabled.
- Explicitly declare module input ports with a net type accepted by VRFC, including enum-typed inputs.
- Preserve path-safe source handling in `src/vivado/sources.tcl`.
- Add local validation that can catch missing explicit input net declarations without requiring Vivado.

**Non-Goals:**

- Do not disable ``default_nettype none``.
- Do not change module port names, widths, directions, or external top-level behavior.
- Do not remove the simulation stage from the default project-mode flow.
- Do not replace the Vivado simulator with another simulator for this flow.

## Decisions

1. Use explicit input net declarations instead of relaxing nettype strictness.

   RTL module inputs will use forms such as `input wire logic clk_i` and `input wire edram_req_e req_op_i`. This satisfies Vivado VRFC while preserving the typo protection provided by ``default_nettype none``.

   Alternative considered: remove or locally override ``default_nettype none``. That would hide the reported error but reduce lint coverage across the RTL.

2. Apply the declaration style consistently across RTL modules.

   The console stops first in `cmd_dispatcher.sv`, but the same `input logic` pattern appears across the RTL. Applying the style once across all module input ports prevents a sequence of one-module-at-a-time Vivado failures.

   Alternative considered: patch only `cmd_dispatcher.sv`. That would likely expose the same VRFC error in subsequent modules.

3. Keep `sources.tcl` path-safe behavior as an invariant.

   The source helper should continue to assert source existence and query `get_files` per resolved path. This avoids the earlier `Too many positional options` failure and keeps Windows-directory runs reliable.

   Alternative considered: move source handling entirely into `run_project_mode.tcl`. That would duplicate source-list ownership already centralized in `sources.tcl`.

## Risks / Trade-offs

- [Risk] `input wire logic` may be unfamiliar to readers used to `input logic`.
  Mitigation: restrict it to module input ports and leave outputs/internal signals in the existing style.

- [Risk] A local static check cannot prove Vivado simulation will pass.
  Mitigation: combine grep/static checks with the existing cocotb/Verilator tests locally, then rerun the project-mode script in Vivado on Windows for final confirmation.

- [Risk] Additional Vivado 2019.1 parser issues may appear after this first compile blocker is fixed.
  Mitigation: treat this change as the first compile compatibility pass and record any later VRFC errors from the next Tcl console run.

## Migration Plan

1. Update RTL module input declarations to include explicit net types.
2. Add a validation check for `input logic` and package-typed `input` declarations without `wire`.
3. Run available local tests and static checks.
4. Rerun `src/vivado/run_project_mode.tcl` from the Windows Vivado GUI/Tcl console and inspect `xvlog.log`.

Rollback is a normal Git revert of the declaration-only RTL edits and validation additions.

## Open Questions

- Vivado is not available in this Linux workspace, so final xsim confirmation must be performed in the Windows Vivado installation that produced the Tcl console log.
