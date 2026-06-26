## 1. Failure Reproduction and Scope

- [x] 1.1 Record the latest Vivado Tcl console root cause in implementation notes, including the successful `$finish` checkpoint and the final `wrong # args: should be "run"` failure
- [x] 1.2 Confirm the current failure is in `edram_project::run_simulation` post-run Tcl sequencing, not RTL compile, elaboration, or testbench stimulus
- [x] 1.3 Verify the default stage order still requires simulation before synthesis

## 2. Simulation Flow Fix

- [x] 2.1 Update `src/vivado/run_project_mode.tcl` so `edram_project::run_simulation` does not call `run all` after `launch_simulation` has completed the generated xsim batch run
- [x] 2.2 Preserve `catch`-based failure propagation for `launch_simulation -simset sim_1 -mode behavioral`
- [x] 2.3 Keep `close_sim` as best-effort cleanup that cannot convert a successful simulation into failure
- [x] 2.4 Confirm success logging only happens after the primary simulation command completes without error

## 3. Validation

- [x] 3.1 Run existing static Tcl validation with `::EDRAM_VIVADO_VALIDATE_ONLY=1`
- [x] 3.2 Add or run a targeted static check that `run_simulation` no longer contains the obsolete post-launch `run all` command
- [x] 3.3 Re-run available local tests or syntax checks that do not require Vivado
- [ ] 3.4 Run the project-mode Tcl flow in Windows Vivado and confirm xsim completion advances to the next enabled stage instead of exiting with `Simulation failed: wrong # args: should be "run"`

## 4. Documentation and OpenSpec Closure

- [x] 4.1 Update project documentation or implementation notes with the corrected Vivado rerun checkpoints
- [x] 4.2 Run `openspec validate fix-vivado-xsim-post-run-status --strict`
- [x] 4.3 Re-run `openspec status --change fix-vivado-xsim-post-run-status` and confirm all artifacts are apply-ready

## Implementation Notes

- 2026-06-26: Latest Windows Vivado 2019.1 log shows xsim compile, elaboration, and simulation completed; the smoke testbench printed `edram_pl_board_top_vivado_tb completed` and reached `$finish` at 357500 ps.
- 2026-06-26: The flow then closed the simulator and failed in `edram_project::run_simulation` with `Simulation failed: wrong # args: should be "run"`, matching the wrapper's post-`launch_simulation` `run all` command rather than an RTL/testbench failure.
- 2026-06-26: Confirmed `src/vivado/run_project_mode.tcl` keeps default stages ordered as `project sources constraints simulate synth impl bitstream`, so simulation remains before synthesis.
- 2026-06-26: Updated `edram_project::run_simulation` to remove the post-`launch_simulation` `run all`; `launch_simulation -simset sim_1 -mode behavioral` remains inside the `catch`, `close_sim` remains best-effort cleanup, and `Vivado simulation completed` is logged only after the catch result is checked.
- 2026-06-26: `tclsh` validate-only run passed with `::EDRAM_VIVADO_VALIDATE_ONLY=1`.
- 2026-06-26: Targeted `awk` scan of `edram_project::run_simulation` found no bare `run all` command after the fix.
- 2026-06-26: `python -m json.tool src/vivado/config.json >/dev/null` passed.
- 2026-06-26: `python scripts/check_vivado_explicit_input_nets.py` passed, checking 11 SystemVerilog files.
- 2026-06-26: `conda run -n track4-fa python sim/tb/run_cocotb.py` passed.
- 2026-06-26: `command -v vivado` did not find Vivado in this Linux workspace; Windows Vivado rerun remains required for task 3.4.
- 2026-06-26: Updated `doc/Vivado-project-mode-flow.md` Windows Vivado checkpoints to require no `Simulation failed: wrong # args: should be "run"` after smoke simulation completion.
- 2026-06-26: `openspec validate fix-vivado-xsim-post-run-status --strict` passed.
- 2026-06-26: `openspec status --change fix-vivado-xsim-post-run-status` reported all 4 artifacts complete and apply-ready.
