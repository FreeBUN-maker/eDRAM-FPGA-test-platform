## ADDED Requirements

### Requirement: Output snapshot payload layout
The system SHALL encode each eDRAM output-port snapshot as five payload bytes containing every FPGA-driven eDRAM output signal.

Snapshot byte layout:

```text
S0 bit0    edram_load_n_o
S0 bit1    edram_read_n_o
S0 bit2    edram_en_wwl_n_o
S0 bit3    edram_en_rwl_n_o
S0 bit7:4  0

S1 bit2:0  edram_wg_o[2:0]
S1 bit5:3  edram_rg_o[2:0]
S1 bit7:6  0

S2         edram_din_o[7:0]
S3 bit5:0  edram_a_o[5:0]
S3 bit7:6  0
S4 bit5:0  edram_w_o[5:0]
S4 bit7:6  0
```

#### Scenario: Snapshot bytes decode all output signals
- **WHEN** the FPGA returns an output snapshot payload `[S0] [S1] [S2] [S3] [S4]`
- **THEN** the PC SHALL be able to recover `LOAD_N`, `READ_N`, `EN_WWL_N`, `EN_RWL_N`, `WG`, `RG`, `DIN`, `A`, and `W` using the documented bit mapping
- **AND** all reserved bits SHALL be returned as `0`

### Requirement: Live output snapshot command
The system SHALL support `READ_OUTPUTS` (`OP=0x06`) to return the current eDRAM output-port snapshot.

#### Scenario: Live output snapshot returned
- **WHEN** the PC sends `READ_OUTPUTS` with no request payload
- **THEN** the FPGA SHALL return an ACK response with exactly five data bytes encoded as an output snapshot
- **AND** the command SHALL NOT start an eDRAM read or write transaction

#### Scenario: Bad live snapshot length rejected
- **WHEN** the PC sends `READ_OUTPUTS` with any request payload
- **THEN** the FPGA SHALL return `NACK_BAD_LEN`
- **AND** the eDRAM controller SHALL remain idle

### Requirement: Output trace snapshot command
The system SHALL support `READ_OUTPUT_TRACE` (`OP=0x07`) to return one captured output-port trace record from the latest eDRAM transaction.

#### Scenario: Output trace record returned
- **WHEN** the PC sends `READ_OUTPUT_TRACE` with a valid one-byte `INDEX`
- **THEN** the FPGA SHALL return an ACK response payload `[COUNT] [INDEX] [S0] [S1] [S2] [S3] [S4]`
- **AND** `[S0]` through `[S4]` SHALL encode the selected captured output snapshot
- **AND** `COUNT` SHALL report the number of valid trace records available for the latest transaction

#### Scenario: Output trace index rejected
- **WHEN** the PC sends `READ_OUTPUT_TRACE` with an `INDEX` greater than or equal to the available `COUNT`
- **THEN** the FPGA SHALL return `NACK_BAD_ARG`
- **AND** the eDRAM controller SHALL remain idle

#### Scenario: Bad trace request length rejected
- **WHEN** the PC sends `READ_OUTPUT_TRACE` without exactly one payload byte
- **THEN** the FPGA SHALL return `NACK_BAD_LEN`
- **AND** the eDRAM controller SHALL remain idle
