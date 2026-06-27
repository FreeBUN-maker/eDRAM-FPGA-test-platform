# edram-control-timing Specification

## Purpose
TBD - created by archiving change define-pl-only-fpga-design. Update Purpose after archive.
## Requirements
### Requirement: eDRAM idle output values
The system SHALL drive the eDRAM interface to documented idle values whenever reset is active, no transaction is running, or the controller is recovering from an error.

#### Scenario: Idle values after reset
- **WHEN** reset is asserted or the eDRAM controller enters idle
- **THEN** `LOAD`, `READ`, `EN-WWL`, and `EN-RWL` SHALL be driven high
- **AND** `WG[2:0]`, `RG[2:0]`, `DIN[7:0]`, `A[5:0]`, and `W[5:0]` SHALL be driven to zero

#### Scenario: Error recovery returns idle
- **WHEN** the eDRAM controller detects a timeout or receives a soft reset request
- **THEN** all eDRAM output controls SHALL return to idle values before the controller reports idle

### Requirement: Parameterized timing windows
The system SHALL implement eDRAM setup, pulse, sample, recovery, and timeout delays as clock-cycle parameters rather than fixed one-cycle assumptions.

#### Scenario: Configured wait counts observed
- **WHEN** the controller executes a read or write transaction
- **THEN** each setup, pulse, sample, and recovery state SHALL remain active for the configured number of PL clock cycles

#### Scenario: Minimum wait count enforced
- **WHEN** a timing parameter is configured for a state that drives an external eDRAM control signal
- **THEN** the RTL SHALL enforce at least one PL clock cycle for that state

### Requirement: Row write group loading
The system SHALL load all eight write groups for a row by presenting stable `WG[2:0]` and `DIN[7:0]` values before pulsing active-low `LOAD` for each group.

#### Scenario: One LOAD pulse per group
- **WHEN** a `WRITE_ROW` micro-operation starts
- **THEN** the controller SHALL iterate group indices `0` through `7`
- **AND** for each group the controller SHALL set `WG[2:0]` and `DIN[7:0]`, wait the configured setup window, assert `LOAD=0`, deassert `LOAD=1`, and wait the configured recovery window

#### Scenario: Group data mapping preserved
- **WHEN** group index `g` is being loaded during a `WRITE_ROW` micro-operation
- **THEN** `WG[2:0]` SHALL equal `g`
- **AND** `DIN[7:0]` SHALL equal the request payload byte for `GROUP=g`

### Requirement: Row write commit
The system SHALL commit a row write only after all eight write groups have been loaded.

#### Scenario: EN-WWL asserted after group loads
- **WHEN** all eight write groups have completed their `LOAD` pulses
- **THEN** the controller SHALL set `A[5:0]` to the requested row, wait the configured row-address setup window, assert `EN-WWL=0` for the configured pulse window, and then deassert `EN-WWL=1`

#### Scenario: Read controls remain idle during write
- **WHEN** the controller is executing a `WRITE_ROW` micro-operation
- **THEN** `READ` and `EN-RWL` SHALL remain high for the entire write transaction

### Requirement: Group read selection and enable timing
The system SHALL perform a group read by stabilizing `W[5:0]` and `RG[2:0]` before active read sampling, then asserting active-low read controls for the configured windows.

#### Scenario: Read address stable before row enable
- **WHEN** a `READ_GROUP` micro-operation starts
- **THEN** the controller SHALL set `W[5:0]` to the requested row and `RG[2:0]` to the requested group before asserting `EN-RWL=0`

#### Scenario: Read controls asserted for configured windows
- **WHEN** the read address and group are stable
- **THEN** the controller SHALL assert `READ=0`, wait the configured read setup window, assert `EN-RWL=0`, and keep the read controls active until the configured pulse and sample requirements are satisfied

#### Scenario: Write controls remain idle during read
- **WHEN** the controller is executing a `READ_GROUP` micro-operation
- **THEN** `LOAD` and `EN-WWL` SHALL remain high for the entire read transaction

### Requirement: Read data sampling
The system SHALL sample `P[7:0]` only after the configured read data settle window has elapsed while the selected read group is active.

#### Scenario: P sampled after settle window
- **WHEN** `EN-RWL=0` has been asserted for the configured sample delay
- **THEN** the controller SHALL capture `P[7:0]` into an internal read-data register
- **AND** the captured byte SHALL be returned to the command dispatcher for the response payload

#### Scenario: Read output returns idle after capture
- **WHEN** the read data byte has been captured and the configured read pulse and recovery windows have elapsed
- **THEN** `EN-RWL` and `READ` SHALL be driven high
- **AND** the controller SHALL report the read micro-operation complete

### Requirement: Controller timeout
The system SHALL include a timeout mechanism that prevents any eDRAM control signal from remaining active indefinitely.

#### Scenario: Timeout aborts active transaction
- **WHEN** a read or write micro-operation exceeds `CTRL_TIMEOUT_CYCLES`
- **THEN** the controller SHALL abort the active transaction
- **AND** all eDRAM output controls SHALL return to idle values
- **AND** the dispatcher SHALL be able to report `NACK_TIMEOUT`

#### Scenario: No timeout on normal completion
- **WHEN** a read or write micro-operation completes before `CTRL_TIMEOUT_CYCLES`
- **THEN** the controller SHALL report successful completion
- **AND** the dispatcher SHALL NOT report `NACK_TIMEOUT` for that operation

