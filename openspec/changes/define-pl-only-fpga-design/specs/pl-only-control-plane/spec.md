## ADDED Requirements

### Requirement: PL-only top-level integration
The system SHALL implement the eDRAM test platform control path entirely in FPGA PL logic, without requiring PS-side software, AXI register access, DMA, or interrupts for normal UART-controlled read/write operation.

#### Scenario: Top-level reset enters idle state
- **WHEN** the PL top-level reset is asserted
- **THEN** the UART parser, command dispatcher, response encoder, and eDRAM controller SHALL return to their idle states
- **AND** the eDRAM output controls SHALL be driven to documented idle values

#### Scenario: Command path uses only PL interfaces
- **WHEN** the top-level receives a valid UART request frame on the PL UART RX pin
- **THEN** the request SHALL be parsed, executed, and answered using PL modules connected to UART and eDRAM pins
- **AND** no PS-side transaction SHALL be required to complete the request

### Requirement: UART frame parser
The system SHALL parse byte-oriented UART request frames using the documented `SOF=0x55`, `LEN`, `OP`, `ARGS`, and XOR `CHK` fields.

#### Scenario: Valid request frame accepted
- **WHEN** the UART receiver delivers a complete request frame with `SOF=0x55`, a supported `LEN`, and a valid XOR checksum
- **THEN** the frame parser SHALL emit exactly one parsed command containing `OP` and `ARGS`

#### Scenario: Invalid SOF ignored
- **WHEN** the UART receiver delivers a byte that is not `0x55` while the parser is waiting for a new frame
- **THEN** the parser SHALL discard the byte
- **AND** the response encoder SHALL NOT transmit a response for that byte

#### Scenario: Bad checksum rejected
- **WHEN** the parser receives a complete request frame whose checksum does not match the XOR checksum rule
- **THEN** the system SHALL return `NACK_BAD_CHK`
- **AND** the eDRAM controller SHALL NOT start a read or write transaction

### Requirement: Command dispatcher validation
The system SHALL validate opcode, payload length, row address, and group address before starting any eDRAM transaction.

#### Scenario: Unsupported opcode rejected
- **WHEN** the dispatcher receives a validly framed request with an unsupported `OP`
- **THEN** the system SHALL return `NACK_BAD_OP`
- **AND** the eDRAM controller SHALL remain idle

#### Scenario: Invalid payload length rejected
- **WHEN** the dispatcher receives a supported `OP` whose `LEN` does not match the documented payload size
- **THEN** the system SHALL return `NACK_BAD_LEN`
- **AND** the eDRAM controller SHALL remain idle

#### Scenario: Out-of-range address rejected
- **WHEN** the dispatcher receives a row value greater than `63` or a group value greater than `7`
- **THEN** the system SHALL return `NACK_BAD_ARG`
- **AND** the eDRAM controller SHALL remain idle

### Requirement: Supported UART commands
The system SHALL support `PING`, `WRITE_ROW`, `READ_GROUP`, `READ_ROW`, `RESET`, and `STATUS` commands with the opcode and payload semantics documented for the UART protocol.

#### Scenario: PING returns connectivity payload
- **WHEN** the dispatcher receives a valid `PING` request
- **THEN** the system SHALL return an ACK response with payload `0xA5`
- **AND** the eDRAM controller SHALL remain idle

#### Scenario: WRITE_ROW starts one row-write transaction
- **WHEN** the dispatcher receives a valid `WRITE_ROW` request containing one row and eight data bytes
- **THEN** the dispatcher SHALL issue one row-write transaction to the eDRAM controller
- **AND** the system SHALL return ACK only after the controller reports completion

#### Scenario: READ_GROUP returns one data byte
- **WHEN** the dispatcher receives a valid `READ_GROUP` request containing one row and one group
- **THEN** the dispatcher SHALL issue one group-read transaction to the eDRAM controller
- **AND** the system SHALL return ACK with one data byte sampled from `P[7:0]`

#### Scenario: READ_ROW returns groups in order
- **WHEN** the dispatcher receives a valid `READ_ROW` request containing one row
- **THEN** the dispatcher SHALL issue group-read transactions for groups `0` through `7` in ascending order
- **AND** the system SHALL return ACK with eight data bytes ordered by group index

#### Scenario: RESET clears controller-visible state
- **WHEN** the dispatcher receives a valid `RESET` request
- **THEN** the system SHALL force the eDRAM controller and parser-visible status back to idle
- **AND** the system SHALL return ACK

#### Scenario: STATUS reports busy and last error
- **WHEN** the dispatcher receives a valid `STATUS` request
- **THEN** the system SHALL return ACK with `[STATE] [LAST_ERR]`
- **AND** `STATE[0]` SHALL report whether an eDRAM transaction is busy

### Requirement: UART response encoder
The system SHALL encode every completed or rejected valid request as a UART response frame using `SOF_R=0xAA`, `LEN`, `STATUS`, `OP_ECHO`, optional `DATA`, and XOR `CHK`.

#### Scenario: ACK response emitted
- **WHEN** a supported command completes successfully
- **THEN** the response encoder SHALL transmit `[0xAA] [LEN] [0x00] [OP_ECHO] [DATA...] [CHK]`
- **AND** `CHK` SHALL equal the XOR of `LEN`, `STATUS`, `OP_ECHO`, and response data bytes

#### Scenario: NACK response emitted
- **WHEN** a validly framed request is rejected after parsing
- **THEN** the response encoder SHALL transmit a response with a non-zero `STATUS`
- **AND** `OP_ECHO` SHALL identify the rejected request when the opcode is known

### Requirement: Single in-flight transaction flow control
The system SHALL execute at most one eDRAM transaction at a time.

#### Scenario: Busy command rejected
- **WHEN** a parsed request would start an eDRAM transaction while the controller is already busy
- **THEN** the system SHALL return `NACK_BUSY`
- **AND** the currently executing transaction SHALL continue unaffected

#### Scenario: Host waits for response
- **WHEN** the PC host sends one request and waits until the corresponding response frame is received
- **THEN** the FPGA SHALL preserve request/response ordering for all supported commands
