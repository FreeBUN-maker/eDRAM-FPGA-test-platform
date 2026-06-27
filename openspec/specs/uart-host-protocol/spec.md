# uart-host-protocol Specification

## Purpose
Defines the byte-oriented UART command and response protocol used by the PC host to control FPGA-side eDRAM read, write, status, reset, and connectivity transactions.

## Requirements
### Requirement: UART frame format
The system SHALL use byte-oriented UART frames for all PC-to-FPGA requests and FPGA-to-PC responses.

#### Scenario: Request frame parsed
- **WHEN** the FPGA receives `[0x55] [LEN] [OP] [ARGS...] [CHK]` with a valid checksum
- **THEN** the FPGA SHALL parse `OP` and `ARGS` as one complete request frame

#### Scenario: Response frame emitted
- **WHEN** the FPGA completes or rejects a request
- **THEN** the FPGA SHALL transmit `[0xAA] [LEN] [STATUS] [OP_ECHO] [DATA...] [CHK]`

### Requirement: Checksum validation
The system SHALL validate each request checksum before executing the requested command.

#### Scenario: Bad checksum rejected
- **WHEN** the FPGA receives a frame whose checksum does not match the XOR checksum rule
- **THEN** the FPGA SHALL reject the command and return a NACK response without changing the eDRAM control state

### Requirement: Write row command
The system SHALL support a `WRITE_ROW` command that writes eight 8-bit groups to one eDRAM row.

#### Scenario: Successful row write
- **WHEN** the PC sends `WRITE_ROW` with a row in `0..63` and eight data bytes
- **THEN** the FPGA SHALL load the eight WBL groups and commit the selected row through the eDRAM write FSM

### Requirement: Read group command
The system SHALL support a `READ_GROUP` command that reads one 8-bit RBL group from one eDRAM row.

#### Scenario: Successful group read
- **WHEN** the PC sends `READ_GROUP` with a row in `0..63` and a group in `0..7`
- **THEN** the FPGA SHALL read the selected group and return one data byte in the response payload

### Requirement: Read row command
The system SHALL support a `READ_ROW` command that reads all eight 8-bit RBL groups from one eDRAM row.

#### Scenario: Successful row read
- **WHEN** the PC sends `READ_ROW` with a row in `0..63`
- **THEN** the FPGA SHALL read groups `0..7` and return eight data bytes in group order

### Requirement: Control commands
The system SHALL support reset, status, and ping commands for host-side control and debug.

#### Scenario: Reset command
- **WHEN** the PC sends `RESET`
- **THEN** the FPGA SHALL return all eDRAM control signals and parser state to the documented idle state

#### Scenario: Status command
- **WHEN** the PC sends `STATUS`
- **THEN** the FPGA SHALL return a response payload describing whether the controller is idle or busy

#### Scenario: Ping command
- **WHEN** the PC sends `PING`
- **THEN** the FPGA SHALL return an ACK response with the documented ping payload

### Requirement: Error handling
The system SHALL return NACK responses for malformed or unsupported requests.

#### Scenario: Unsupported opcode
- **WHEN** the FPGA receives a validly framed request with an unsupported opcode
- **THEN** the FPGA SHALL return a bad-opcode NACK response

#### Scenario: Invalid argument
- **WHEN** the FPGA receives an out-of-range row, out-of-range group, or invalid payload length
- **THEN** the FPGA SHALL return a NACK response and SHALL NOT start an eDRAM transaction
