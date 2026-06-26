# vivado-config-json Specification

## Purpose
Defines the machine-readable Vivado configuration JSON used to create the PL-only eDRAM test platform build, including project metadata, RTL source ordering, clock metadata, port constraints, and unresolved-pin safety rules.

## Requirements
### Requirement: Vivado project metadata
The Vivado configuration JSON SHALL define the project metadata required to create the FPGA build for the PL-only eDRAM test platform.

#### Scenario: Target device is configured
- **WHEN** `src/vivado/config.json` is loaded
- **THEN** the project metadata SHALL identify the target part as `xczu5ev-sfvc784-1-i`
- **AND** the top module SHALL identify the board-level top `edram_pl_board_top`

#### Scenario: Metadata is machine readable
- **WHEN** a Tcl or validation script parses the configuration file
- **THEN** the file SHALL be valid JSON
- **AND** project metadata SHALL be represented as structured fields rather than comments or free-form text

### Requirement: RTL source list
The Vivado configuration JSON SHALL list the SystemVerilog source files needed to build the board-level eDRAM test platform top.

#### Scenario: Required RTL files are included
- **WHEN** the source list is inspected
- **THEN** it SHALL include `src/rtl/edram_pkg.sv`, `src/rtl/uart_baud_gen.sv`, `src/rtl/uart_rx.sv`, `src/rtl/uart_tx.sv`, `src/rtl/uart_frame_parser.sv`, `src/rtl/uart_resp_encoder.sv`, `src/rtl/cmd_dispatcher.sv`, `src/rtl/edram_ctrl_fsm.sv`, `src/rtl/edram_pl_top.sv`, `src/rtl/pl_clk_diff_to_single.sv`, and `src/rtl/edram_pl_board_top.sv`

#### Scenario: Package source precedes dependents
- **WHEN** the source list is consumed in order
- **THEN** `src/rtl/edram_pkg.sv` SHALL appear before source files that import `edram_pkg`

### Requirement: Clock constraint configuration
The Vivado configuration JSON SHALL define the board PL clock input and generated core clock metadata needed for timing constraint generation and review.

#### Scenario: Differential board clock ports are described
- **WHEN** the clock configuration is inspected
- **THEN** it SHALL identify `pl_clk0_p_i` and `pl_clk0_n_i` as the physical differential clock ports
- **AND** it SHALL include clock name, input frequency in Hz, input period in ns, package pins, I/O standard, and manual provenance

#### Scenario: Generated core clock metadata is described
- **WHEN** the clock configuration is inspected
- **THEN** it SHALL include generated clock metadata for the single-ended core clock
- **AND** it SHALL record the generated frequency and MMCM multiply/divide parameters used by `pl_clk_diff_to_single`

### Requirement: Top-level port constraints
The Vivado configuration JSON SHALL represent every external port on `edram_pl_board_top` with direction, width, I/O standard, and package pin information.

#### Scenario: Scalar ports are represented
- **WHEN** the port constraints are inspected
- **THEN** they SHALL include `pl_clk0_p_i`, `pl_clk0_n_i`, `rst_ni`, `uart_rx_i`, `uart_tx_o`, `edram_load_n_o`, `edram_read_n_o`, `edram_en_wwl_n_o`, and `edram_en_rwl_n_o`

#### Scenario: Bus ports are represented with bit order
- **WHEN** the port constraints are inspected
- **THEN** they SHALL include bit-ordered entries for `edram_wg_o[2:0]`, `edram_rg_o[2:0]`, `edram_din_o[7:0]`, `edram_a_o[5:0]`, `edram_w_o[5:0]`, and `edram_p_i[7:0]`

#### Scenario: Direction matches RTL
- **WHEN** a validation script compares the JSON port entries with `edram_pl_board_top.sv`
- **THEN** input ports SHALL be marked as inputs
- **AND** output ports SHALL be marked as outputs

### Requirement: Pin mapping traceability
The Vivado configuration JSON SHALL keep package pin mappings traceable to the board manual or an explicit user-provided mapping.

#### Scenario: Confirmed pin includes provenance
- **WHEN** a port bit has a confirmed package pin
- **THEN** the configuration SHALL include the package pin name
- **AND** it SHALL include a board connector or manual-reference field sufficient for review

#### Scenario: Unconfirmed pin is not guessed
- **WHEN** a port bit package pin cannot be confirmed
- **THEN** the configuration SHALL leave the package pin unset
- **AND** it SHALL include an unresolved entry explaining what information is still required

### Requirement: Tcl constraint generation safety
The Vivado configuration JSON SHALL contain enough information for Tcl scripts to decide whether clock and pin constraints can be generated safely.

#### Scenario: Complete mapping can generate XDC
- **WHEN** all required package pins and I/O standards are present
- **THEN** the Vivado Tcl flow SHALL be able to generate `create_clock`, `set_property PACKAGE_PIN`, and `set_property IOSTANDARD` constraints from the JSON

#### Scenario: Incomplete mapping stops final XDC generation
- **WHEN** required pin mappings remain unresolved
- **THEN** the Vivado Tcl flow SHALL report the unresolved ports
- **AND** it SHALL stop before generating a final pin XDC that could be mistaken for board-ready constraints
