## ADDED Requirements

### Requirement: Output snapshot RTL source metadata
The Vivado configuration JSON SHALL include the RTL source file that implements eDRAM output-port snapshot and trace readback when that logic is added to the design.

#### Scenario: Snapshot RTL source is listed
- **WHEN** `src/vivado/config.json` is inspected after output-port UART readback is implemented
- **THEN** the `sources` array SHALL include `src/rtl/edram_output_snapshot.sv`
- **AND** `src/rtl/edram_output_snapshot.sv` SHALL appear after `src/rtl/edram_pkg.sv` and before `src/rtl/edram_pl_top.sv`
