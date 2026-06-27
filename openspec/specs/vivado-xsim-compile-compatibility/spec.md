# vivado-xsim-compile-compatibility Specification

## Purpose
Defines the RTL declaration and Vivado source-helper compatibility requirements needed for Vivado 2019.1 xsim/VRFC to compile the board-level SystemVerilog design under strict ``default_nettype none`` settings.
## Requirements
### Requirement: Strict-nettype RTL compiles in Vivado xsim
The board-level SystemVerilog RTL SHALL be declaration-compatible with Vivado 2019.1 VRFC while ``default_nettype none`` is active.

#### Scenario: Module inputs declare explicit net types
- **WHEN** Vivado xsim analyzes RTL files that contain ``default_nettype none``
- **THEN** every module input port SHALL explicitly declare a net type such as `wire`
- **AND** the declaration SHALL preserve the existing signal data type, width, and direction

#### Scenario: Package-typed inputs are explicit
- **WHEN** a module input uses a package-defined type such as `edram_req_e`
- **THEN** the input declaration SHALL include an explicit net type
- **AND** Vivado VRFC SHALL NOT need an implicit default net type for that port

### Requirement: Vivado source helper handles Windows project paths
The Vivado source helper SHALL add and query RTL source files without passing a multi-file path list as unsupported positional arguments to Vivado commands.

#### Scenario: Source object lookup is path-safe
- **WHEN** `edram_vivado::add_rtl_sources` adds the configured RTL source list
- **THEN** it SHALL resolve file objects using Vivado queries that accept each source path safely
- **AND** it SHALL avoid the `Too many positional options` error shown by `get_files`

#### Scenario: Missing source fails clearly
- **WHEN** a required RTL source path cannot be found after repository-root resolution
- **THEN** the helper SHALL stop before compile
- **AND** it SHALL report the missing source path

### Requirement: Compile compatibility is validated before closing the fix
The fix SHALL include checks that target the reported xsim compile failure and preserve the default project-mode flow.

#### Scenario: Local static compatibility check passes
- **WHEN** validation is run outside Vivado
- **THEN** it SHALL check that RTL module input ports no longer rely on implicit net types under ``default_nettype none``

#### Scenario: Vivado simulation remains the default gate
- **WHEN** the project-mode Tcl script is run with default stages in Vivado
- **THEN** it SHALL still launch the behavioral simulation before synthesis
- **AND** it SHALL stop subsequent stages if xsim compile or simulation fails
