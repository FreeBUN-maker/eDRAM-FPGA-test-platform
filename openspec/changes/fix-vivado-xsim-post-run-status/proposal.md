## Why

Vivado 2019.1 xsim now compiles, elaborates, and runs the smoke testbench, but the project-mode Tcl flow still exits after simulation. The latest Tcl console log shows the testbench reaches `$finish`, then the wrapper reports `Simulation failed: wrong # args: should be "run"` because the script issues a post-launch `run all` after Vivado has already completed the batch simulation.

## What Changes

- Update the Vivado project-mode simulation stage so a completed xsim smoke test is treated as success.
- Avoid issuing simulator commands that are invalid after `launch_simulation` has already run the batch testbench to completion.
- Preserve fail-fast behavior when xsim compile, elaboration, or simulation actually reports an error.
- Add local validation that exercises the Tcl control path enough to prevent this regression from returning.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `vivado-project-mode-tcl`: Clarify that the simulation stage must distinguish successful xsim completion from post-run Tcl command errors, and must not report failure after a successful smoke test.

## Impact

- Affected script: `src/vivado/run_project_mode.tcl`.
- Affected verification flow: Vivado GUI/Tcl users running the default full flow should proceed from successful behavioral simulation into synthesis instead of stopping at a false simulation failure.
- Affected tests/checks: local Tcl validation should cover simulation command sequencing where possible; full confirmation still requires Vivado.

## Non-goals

- Do not change RTL behavior, UART protocol behavior, eDRAM timing, board constraints, or top-level ports.
- Do not skip Vivado behavioral simulation in the default flow.
- Do not suppress real xsim compile, elaboration, simulation, or testbench assertion failures.
- Do not introduce a dependency on non-Vivado simulators for the project-mode flow.
