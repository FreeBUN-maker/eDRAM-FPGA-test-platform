## ADDED Requirements

### Requirement: Output snapshot RTL source in Tcl helper
The Vivado Tcl source helper SHALL add the output snapshot RTL source in the maintained RTL compile order.

#### Scenario: Tcl source resolver includes snapshot RTL
- **WHEN** `edram_vivado::resolve_rtl_sources` is called after output-port UART readback is implemented
- **THEN** the returned source list SHALL include `src/rtl/edram_output_snapshot.sv`
- **AND** `src/rtl/edram_output_snapshot.sv` SHALL appear after `src/rtl/edram_pkg.sv` and before `src/rtl/edram_pl_top.sv`

#### Scenario: Tcl source adder validates snapshot RTL exists
- **WHEN** `edram_vivado::add_rtl_sources` or `edram_vivado::read_rtl_sources` is called
- **THEN** the helper SHALL fail early if `src/rtl/edram_output_snapshot.sv` is missing
- **AND** the Vivado project SHALL NOT proceed with an incomplete RTL source set
