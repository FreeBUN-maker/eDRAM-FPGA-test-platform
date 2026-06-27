## ADDED Requirements

### Requirement: Output-port snapshot source
The PL-only control plane SHALL sample eDRAM output snapshots from the same logic nets that drive the top-level eDRAM output ports.

#### Scenario: Snapshot observes top-level output drive nets
- **WHEN** `edram_pl_top` drives `edram_load_n_o`, `edram_read_n_o`, `edram_en_wwl_n_o`, `edram_en_rwl_n_o`, `edram_wg_o`, `edram_rg_o`, `edram_din_o`, `edram_a_o`, and `edram_w_o`
- **THEN** the output snapshot logic SHALL sample those driven values from the output-port drive nets
- **AND** it SHALL NOT reconstruct the snapshot only from UART command arguments

#### Scenario: Reset snapshot is idle
- **WHEN** top-level reset or UART `RESET` returns the eDRAM controller to idle
- **THEN** the live output snapshot SHALL report `LOAD_N=1`, `READ_N=1`, `EN_WWL_N=1`, `EN_RWL_N=1`, `WG=0`, `RG=0`, `DIN=0`, `A=0`, and `W=0`

### Requirement: Output snapshot commands do not disturb eDRAM transactions
The PL-only control plane SHALL serve output snapshot readback commands through UART without starting a new eDRAM read or write transaction.

#### Scenario: Live snapshot command leaves controller idle
- **WHEN** the dispatcher receives a valid `READ_OUTPUTS` request while the eDRAM controller is idle
- **THEN** the system SHALL return the current packed output snapshot
- **AND** `edram_req_valid_o` SHALL remain deasserted for that command

#### Scenario: Trace snapshot command leaves controller idle
- **WHEN** the dispatcher receives a valid `READ_OUTPUT_TRACE` request while the eDRAM controller is idle
- **THEN** the system SHALL return the selected trace snapshot or a validation NACK
- **AND** `edram_req_valid_o` SHALL remain deasserted for that command

### Requirement: Output trace capture
The PL-only control plane SHALL keep a queryable trace of active eDRAM output snapshots from the latest eDRAM transaction.

#### Scenario: Trace cleared at transaction start
- **WHEN** a new `WRITE_ROW`, `READ_GROUP`, or `READ_ROW` eDRAM transaction is accepted by the controller
- **THEN** the previous output trace SHALL be cleared before records for the new transaction are captured

#### Scenario: Active output changes are recorded
- **WHEN** any of `LOAD_N`, `READ_N`, `EN_WWL_N`, or `EN_RWL_N` is active low during an eDRAM transaction
- **AND** the packed output snapshot differs from the most recently captured trace record
- **THEN** the snapshot SHALL be appended to the trace until the configured trace depth is full

#### Scenario: Write row trace contains host-checkable signals
- **WHEN** a `WRITE_ROW` transaction writes eight data groups to a selected row
- **THEN** the output trace SHALL contain records sufficient for the host to verify the driven `WG` and `DIN` value for each written group
- **AND** it SHALL contain a record sufficient for the host to verify the driven row address `A` during row write enable
