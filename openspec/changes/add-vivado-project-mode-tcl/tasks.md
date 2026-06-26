## 1. Project Flow Script Foundation

- [ ] 1.1 Add `src/vivado/run_project_mode.tcl` with GUI-safe repository root detection based on `[info script]`
- [ ] 1.2 Add helper procedures for normalized path construction, required file checks, stage logging, and Tcl error reporting
- [ ] 1.3 Read `project.name`, `project.part`, `project.top`, `project.default_library`, and `project.target_language` from `src/vivado/config.json`
- [ ] 1.4 Add documented defaults for generated project directory, overwrite/open-existing behavior, and full-flow stage selection
- [ ] 1.5 Validate stage override handling, including rejection of unknown stage names

## 2. Vivado Project Setup

- [ ] 2.1 Create or open the Vivado project under `build/vivado/<project-name>/` according to the overwrite setting
- [ ] 2.2 Set project target part, target language, default library, and board top from `config.json`
- [ ] 2.3 Source `src/vivado/sources.tcl` and call `edram_vivado::add_rtl_sources` to populate `sources_1`
- [ ] 2.4 Set the top module on `sources_1` and update compile order
- [ ] 2.5 Add `src/vivado/edram_pl_board.xdc` to `constrs_1` with synthesis and implementation usage enabled

## 3. Vivado Simulation Support

- [ ] 3.1 Add `sim/tb/edram_pl_board_top_vivado_tb.sv` as a SystemVerilog xsim smoke testbench for `edram_pl_board_top`
- [ ] 3.2 Instantiate the board top with `CLK_SIM_BYPASS=1'b1`, differential clock stimulus, reset stimulus, UART idle input, and stable eDRAM readback inputs
- [ ] 3.3 Add the smoke testbench to `sim_1` and configure the simulation top
- [ ] 3.4 Run `launch_simulation` when the simulation stage is enabled and fail the Tcl flow if simulation fails

## 4. Synthesis Implementation and Bitstream

- [ ] 4.1 Configure `synth_1` and launch synthesis when the synthesis stage is enabled
- [ ] 4.2 Wait for `synth_1` completion and check the run status before implementation starts
- [ ] 4.3 Configure and launch `impl_1` through the bitstream generation step when implementation/bitstream stages are enabled
- [ ] 4.4 Wait for `impl_1` completion and check the run status before reporting success
- [ ] 4.5 Locate and log the generated `.bit` file path

## 5. Validation and Documentation

- [ ] 5.1 Run static repository checks confirming the new Tcl script, XDC, sources helper, config JSON, and Vivado smoke testbench paths exist
- [ ] 5.2 Run a syntax-oriented Tcl check where available outside Vivado, or document why Vivado-only commands require Vivado validation
- [ ] 5.3 When Vivado is available, run the script from Vivado GUI `Tools -> Run Tcl Script` or equivalent Tcl mode and record the result
- [ ] 5.4 Update README or `doc/` usage notes with the GUI execution path, generated output directory, stage override examples, and expected bitstream location
- [ ] 5.5 Re-run `openspec status --change add-vivado-project-mode-tcl` and confirm the change remains apply-ready
