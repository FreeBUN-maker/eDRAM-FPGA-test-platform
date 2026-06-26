## ADDED Requirements

### Requirement: GUI-runnable project mode entry point
The system SHALL provide a Vivado project mode Tcl script that can be executed directly through Vivado GUI `Tools -> Run Tcl Script`.

#### Scenario: Script locates repository inputs from Vivado GUI
- **WHEN** the script is executed from Vivado GUI with an arbitrary current working directory
- **THEN** it SHALL derive the repository root from the script location
- **AND** it SHALL locate `src/vivado/config.json`, `src/vivado/sources.tcl`, and `src/vivado/edram_pl_board.xdc` relative to that repository root

#### Scenario: Missing required input fails early
- **WHEN** any required Vivado input file is missing
- **THEN** the script SHALL stop before creating or running the project flow
- **AND** it SHALL report which required file is missing

### Requirement: Project metadata consumption
The Tcl flow SHALL create the Vivado project from the existing machine-readable Vivado configuration and helper scripts.

#### Scenario: Project properties are loaded
- **WHEN** `src/vivado/config.json` contains project metadata
- **THEN** the script SHALL use the configured project name, target part, top module, default library, and target language for the Vivado project

#### Scenario: RTL sources are added in maintained order
- **WHEN** the Vivado project is created
- **THEN** the script SHALL source `src/vivado/sources.tcl`
- **AND** it SHALL add the RTL sources through the existing `edram_vivado::add_rtl_sources` helper
- **AND** it SHALL update the compile order for `sources_1`

### Requirement: Board constraints are defined
The Tcl flow SHALL add the existing board XDC to the Vivado project constraints fileset.

#### Scenario: Constraint file is attached
- **WHEN** the project is configured
- **THEN** the script SHALL add `src/vivado/edram_pl_board.xdc` to `constrs_1`
- **AND** the file SHALL be used for synthesis and implementation

#### Scenario: Constraint loading is visible
- **WHEN** the constraint file is added
- **THEN** the script SHALL log the normalized XDC path used by the project

### Requirement: Vivado simulation smoke run
The project mode flow SHALL support a Vivado xsim-compatible smoke simulation before synthesis.

#### Scenario: Simulation testbench is available
- **WHEN** simulation is enabled
- **THEN** the project SHALL include a SystemVerilog simulation testbench in `sim/tb`
- **AND** the simulation top SHALL be configured in `sim_1`

#### Scenario: Simulation run completes
- **WHEN** the default full flow is executed
- **THEN** the script SHALL launch Vivado simulation for the configured smoke testbench
- **AND** it SHALL stop the flow if the simulation command fails

### Requirement: Synthesis implementation and bitstream generation
The project mode flow SHALL run Vivado synthesis, implementation, and bitstream generation for the configured board top.

#### Scenario: Synthesis completes before implementation
- **WHEN** the full flow reaches the build stages
- **THEN** the script SHALL launch `synth_1`
- **AND** it SHALL wait for synthesis to complete before launching implementation

#### Scenario: Implementation generates bitstream
- **WHEN** synthesis completes successfully
- **THEN** the script SHALL launch `impl_1` through the bitstream generation step
- **AND** it SHALL wait for implementation and bitstream generation to complete
- **AND** it SHALL report the generated bitstream path

### Requirement: Stage selection and rerun behavior
The Tcl flow SHALL provide deterministic defaults while allowing advanced users to select stages for Tcl console or automation use.

#### Scenario: Default execution runs complete flow
- **WHEN** no stage override is provided
- **THEN** the script SHALL run project creation, source addition, constraint addition, simulation, synthesis, implementation, and bitstream generation

#### Scenario: Stage override limits execution
- **WHEN** a supported stage override is provided before sourcing the script or through a supported environment variable
- **THEN** the script SHALL execute only the requested supported stages
- **AND** it SHALL reject unknown stage names with a clear error

#### Scenario: Existing generated project is handled predictably
- **WHEN** the configured generated project directory already exists
- **THEN** the script SHALL either open the existing project or recreate it according to its documented overwrite setting
- **AND** it SHALL log which behavior was selected

### Requirement: Failure handling and logging
The project mode script SHALL make failures actionable from the Vivado Tcl console and GUI message panes.

#### Scenario: Build run fails
- **WHEN** simulation, synthesis, implementation, or bitstream generation fails
- **THEN** the script SHALL stop subsequent stages
- **AND** it SHALL return a Tcl error that identifies the failed stage

#### Scenario: Successful build reports summary
- **WHEN** the full flow completes successfully
- **THEN** the script SHALL report the project path
- **AND** it SHALL report the bitstream path
