## ADDED Requirements

### Requirement: Host protocol frame helper
The system SHALL provide a host-side Python helper that builds request frames and parses response frames according to the documented UART protocol.

#### Scenario: Documented request examples match
- **WHEN** the helper builds documented `PING`, `RESET`, `STATUS`, `WRITE_ROW`, `READ_GROUP`, and `READ_ROW` requests
- **THEN** each emitted byte sequence SHALL match the examples and checksum rule in `doc/FPGA-PC-UART-interface.md`

#### Scenario: Response frame validation
- **WHEN** the helper parses a response frame with `SOF_R=0xAA`, valid `LEN`, and valid XOR checksum
- **THEN** it SHALL return the decoded status, echoed opcode, payload bytes, and raw frame bytes

#### Scenario: Malformed response rejected
- **WHEN** the helper parses a response frame with bad SOF, bad length, or bad checksum
- **THEN** it SHALL raise a clear protocol error describing the failed validation

### Requirement: Serial transport command exchange
The system SHALL provide a Python serial transport that sends one UART request frame and reads one validated UART response frame from a selected host serial port.

#### Scenario: Configured serial port opened
- **WHEN** the user runs a hardware UART test with `--port`, optional `--baud`, and optional `--timeout`
- **THEN** the script SHALL open the port using 8 data bits, no parity, 1 stop bit, and the configured baud and timeout values

#### Scenario: Response frame read from byte stream
- **WHEN** the FPGA returns a valid response frame after a request
- **THEN** the script SHALL synchronize to `0xAA`, read `LEN`, read the remaining body and checksum bytes, and validate the response before reporting success

#### Scenario: Timeout reported
- **WHEN** the expected response bytes are not received before the configured timeout
- **THEN** the script SHALL fail with a non-zero exit code and an error message that identifies the timed-out command

### Requirement: UART connectivity smoke test
The system SHALL provide a host-side smoke test that verifies the basic bidirectional UART command path without requiring meaningful eDRAM array contents.

#### Scenario: Smoke test success
- **WHEN** the user runs the smoke test against a programmed FPGA board with a working UART path
- **THEN** the script SHALL send `RESET`, `PING`, and `STATUS`, verify ACK responses and expected payload shapes, and exit with code 0

#### Scenario: Ping payload mismatch
- **WHEN** the `PING` response is ACK but its payload is not `[0xA5]`
- **THEN** the smoke test SHALL fail with a diagnostic showing the expected and actual payload bytes

#### Scenario: Status payload decoded
- **WHEN** the `STATUS` response is ACK with two payload bytes
- **THEN** the smoke test SHALL report the decoded busy bit and last-error status name

### Requirement: Optional eDRAM transaction test
The system SHALL provide an opt-in host-side eDRAM transaction test that writes a selected row and verifies readback through the UART command path.

#### Scenario: Row write and readback pass
- **WHEN** the user runs the memory test with a selected row and the eDRAM path returns the written data
- **THEN** the script SHALL send `WRITE_ROW`, read the row with `READ_ROW`, compare all eight returned group bytes, and exit with code 0

#### Scenario: Readback mismatch reported
- **WHEN** any returned group byte differs from the written pattern
- **THEN** the script SHALL fail with a non-zero exit code and report the row, group index, expected byte, and actual byte

#### Scenario: Bad memory-test arguments rejected
- **WHEN** the user provides an out-of-range row, out-of-range group, or malformed pattern
- **THEN** the script SHALL reject the arguments before sending any UART request

### Requirement: Host UART test documentation
The system SHALL document how to install dependencies and run host-side UART tests from the repository root.

#### Scenario: README usage added
- **WHEN** a user reads `README.md`
- **THEN** it SHALL include the required Python dependency, serial-port selection guidance, smoke-test command, ping/status command examples, memory-test command example, and expected pass/fail behavior

#### Scenario: Hardware-free self-test documented
- **WHEN** a user does not have a connected FPGA board
- **THEN** the README SHALL show a command that validates protocol frame helpers without opening a serial port
