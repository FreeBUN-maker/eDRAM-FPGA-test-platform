## 1. Project Flow Script Foundation

- [x] 1.1 Add `src/vivado/run_project_mode.tcl` with GUI-safe repository root detection based on `[info script]`
- [x] 1.2 Add helper procedures for normalized path construction, required file checks, stage logging, and Tcl error reporting
- [x] 1.3 Read `project.name`, `project.part`, `project.top`, `project.default_library`, and `project.target_language` from `src/vivado/config.json`
- [x] 1.4 Add documented defaults for generated project directory, overwrite/open-existing behavior, and full-flow stage selection
- [x] 1.5 Validate stage override handling, including rejection of unknown stage names

## 2. Vivado Project Setup

- [x] 2.1 Create or open the Vivado project under `build/vivado/<project-name>/` according to the overwrite setting
- [x] 2.2 Set project target part, target language, default library, and board top from `config.json`
- [x] 2.3 Source `src/vivado/sources.tcl` and call `edram_vivado::add_rtl_sources` to populate `sources_1`
- [x] 2.4 Set the top module on `sources_1` and update compile order
- [x] 2.5 Add `src/vivado/edram_pl_board.xdc` to `constrs_1` with synthesis and implementation usage enabled

## 3. Vivado Simulation Support

- [x] 3.1 Add `sim/tb/edram_pl_board_top_vivado_tb.sv` as a SystemVerilog xsim smoke testbench for `edram_pl_board_top`
- [x] 3.2 Instantiate the board top with `CLK_SIM_BYPASS=1'b1`, differential clock stimulus, reset stimulus, UART idle input, and stable eDRAM readback inputs
- [x] 3.3 Add the smoke testbench to `sim_1` and configure the simulation top
- [x] 3.4 Run `launch_simulation` when the simulation stage is enabled and fail the Tcl flow if simulation fails

## 4. Synthesis Implementation and Bitstream

- [x] 4.1 Configure `synth_1` and launch synthesis when the synthesis stage is enabled
- [x] 4.2 Wait for `synth_1` completion and check the run status before implementation starts
- [x] 4.3 Configure and launch `impl_1` through the bitstream generation step when implementation/bitstream stages are enabled
- [x] 4.4 Wait for `impl_1` completion and check the run status before reporting success
- [x] 4.5 Locate and log the generated `.bit` file path

## 5. Validation and Documentation

- [x] 5.1 Run static repository checks confirming the new Tcl script, XDC, sources helper, config JSON, and Vivado smoke testbench paths exist
- [x] 5.2 Run a syntax-oriented Tcl check where available outside Vivado, or document why Vivado-only commands require Vivado validation
- [x] 5.3 When Vivado is available, run the script from Vivado GUI `Tools -> Run Tcl Script` or equivalent Tcl mode and record the result
- [x] 5.4 Update README or `doc/` usage notes with the GUI execution path, generated output directory, stage override examples, and expected bitstream location
- [x] 5.5 Re-run `openspec status --change add-vivado-project-mode-tcl` and confirm the change remains apply-ready

## Implementation Notes

- 2026-06-26: `python -m json.tool src/vivado/config.json >/dev/null` passed.
- 2026-06-26: Required-path check passed for `src/vivado/run_project_mode.tcl`, `src/vivado/config.json`, `src/vivado/sources.tcl`, `src/vivado/edram_pl_board.xdc`, `sim/tb/edram_pl_board_top_vivado_tb.sv`, and `doc/Vivado-project-mode-flow.md`.
- 2026-06-26: `tclsh` static validation passed with `::EDRAM_VIVADO_VALIDATE_ONLY=1`.
- 2026-06-26: `tclsh` stage override validation passed for `{project sources constraints simulate}`.
- 2026-06-26: `tclsh` rejected unknown stage `invalid_stage` with a clear error.
- 2026-06-26: `command -v vivado` failed in this environment; Vivado GUI/Tcl-mode xsim, synthesis, implementation, and bitstream execution were not run here.
- 2026-06-26: `openspec status --change add-vivado-project-mode-tcl` reported all artifacts complete.
