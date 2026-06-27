## MODIFIED Requirements

### Requirement: Vivado simulation smoke run
The project mode flow SHALL support a Vivado xsim-compatible smoke simulation before synthesis.

#### Scenario: Simulation testbench is available
- **WHEN** simulation is enabled
- **THEN** the project SHALL include a SystemVerilog simulation testbench in `sim/tb`
- **AND** the simulation top SHALL be configured in `sim_1`

#### Scenario: Simulation run completes
- **WHEN** the default full flow is executed
- **THEN** the script SHALL launch Vivado simulation for the configured smoke testbench
- **AND** it SHALL treat a completed xsim batch run as a successful simulation stage
- **AND** it SHALL NOT issue invalid post-run simulator commands after xsim has already completed the generated simulation batch
- **AND** it SHALL proceed to subsequent enabled stages after successful simulation
- **AND** it SHALL stop the flow if simulation launch, compile, elaboration, or execution fails
