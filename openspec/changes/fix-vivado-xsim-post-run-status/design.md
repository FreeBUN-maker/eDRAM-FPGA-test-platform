## Context

The Vivado project-mode flow launches `sim_1` through `launch_simulation -simset sim_1 -mode behavioral`, then immediately calls `run all` inside the same `catch` block. The reported Vivado 2019.1 log shows xsim compiles, elaborates, loads the snapshot, sources the generated simulation Tcl, reaches the testbench `$finish`, and closes the simulation. Only after that does the wrapper report `Simulation failed: wrong # args: should be "run"`.

This means the simulator result is successful, but the wrapper's post-run command sequence converts that success into a Tcl error. The fix belongs in `src/vivado/run_project_mode.tcl`; RTL, testbench stimulus, and board constraints are not implicated by this failure.

System impact:

```text
Vivado GUI / Tcl console
        |
        v
src/vivado/run_project_mode.tcl
        |
        +--> configure sim_1 top/testbench
        |
        +--> launch_simulation -simset sim_1 -mode behavioral
        |        |
        |        v
        |     xsim batch run reaches testbench $finish
        |
        +--> close_sim best-effort
        |
        v
next enabled stage, normally synthesis
```

Current failing timing:

```text
launch_simulation      generated xsim Tcl       testbench       wrapper
      |                       |                    |               |
      +---------------------->|                    |               |
      |                       +------------------->|               |
      |                       |                 $finish            |
      |<----------------------+                    |               |
      |                       |                    |---- close ---->|
      |                       |                    |               | run all
      |                       |                    |               | -> Tcl error
```

Target timing:

```text
launch_simulation      generated xsim Tcl       testbench       wrapper
      |                       |                    |               |
      +---------------------->|                    |               |
      |                       +------------------->|               |
      |                       |                 $finish            |
      |<----------------------+                    |               |
      |                       |                    |               | close_sim
      |                       |                    |               | success
```

Modules to be revised:

- `src/vivado/run_project_mode.tcl`: `edram_project::run_simulation`

## Goals / Non-Goals

**Goals:**

- Treat a completed Vivado xsim smoke test as a successful simulation stage.
- Preserve Tcl fail-fast behavior for real `launch_simulation` failures.
- Keep the default stage order unchanged so simulation remains the gate before synthesis.
- Keep the script usable from Vivado GUI `Tools -> Run Tcl Script`.

**Non-Goals:**

- Do not alter RTL, testbench behavior, UART/eDRAM protocol semantics, or XDC constraints.
- Do not skip simulation or make synthesis run after real xsim failures.
- Do not add simulator-specific log scraping as the primary pass/fail mechanism.

## Decisions

1. Let `launch_simulation` own the Vivado batch run.

   Vivado generated `edram_pl_board_top_vivado_tb.tcl` already runs the behavioral simulation to the configured time/testbench completion in the reported flow. Calling `run all` afterward is redundant and can be invalid once the batch run has closed. The implementation should catch `launch_simulation` errors directly and avoid a second simulator run command after completion.

   Alternative considered: keep `run all` but only call it when an active simulation is detected. This adds state probing complexity and still duplicates Vivado's generated batch execution.

2. Keep `close_sim` outside the failure decision.

   `close_sim` should remain best-effort cleanup, because the simulator may already be closed after a normal `$finish` or after a launch failure. Its cleanup result should not override the primary `launch_simulation` result.

   Alternative considered: fail if `close_sim` fails. That would reintroduce false negatives for an already-closed successful simulation.

3. Validate with static Tcl checks locally and require Vivado rerun for final confirmation.

   The local environment may not have Vivado, so local validation should at least preserve `EDRAM_VIVADO_VALIDATE_ONLY=1` behavior and include a targeted static check that the obsolete post-launch `run all` command is gone from `run_simulation`. Full validation remains the same Vivado GUI/Tcl rerun that produced the error.

## Risks / Trade-offs

- [Risk] Vivado behavior can vary between GUI project mode and batch Tcl mode. -> Mitigation: keep the fix within documented project-mode command sequencing and ask for a Vivado rerun after implementation.
- [Risk] Removing `run all` could expose a flow where `launch_simulation` only opens the simulator instead of running the testbench. -> Mitigation: verify against the generated Vivado 2019.1 log path where `launch_simulation` sources the testbench Tcl and runs 1000 ns; if needed later, add an explicit pre-launch simulation runtime property instead of post-run commands.
- [Risk] A real testbench failure could still appear as a Tcl success if the testbench only prints errors. -> Mitigation: keep existing xsim command failure propagation; assertion semantics are outside this change.
