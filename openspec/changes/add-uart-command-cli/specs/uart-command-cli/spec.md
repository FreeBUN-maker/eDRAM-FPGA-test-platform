## ADDED Requirements

### Requirement: Direct UART command CLI
The system SHALL provide a host-side Python CLI for sending individual commands from the currently documented FPGA UART protocol.

#### Scenario: Named command sent
- **WHEN** a user runs the CLI with a supported named command and valid arguments
- **THEN** the CLI SHALL build the matching request frame using the documented opcode, payload layout, and XOR checksum rule

#### Scenario: Current command set covered
- **WHEN** a user asks for command help
- **THEN** the CLI SHALL expose commands for `PING`, `RESET`, `STATUS`, `WRITE_ROW`, `READ_GROUP`, `READ_ROW`, `READ_OUTPUTS`, and `READ_OUTPUT_TRACE`

#### Scenario: Invalid command arguments rejected before serial open
- **WHEN** a user provides an out-of-range row, out-of-range group, malformed data byte, or wrong row-data length
- **THEN** the CLI SHALL fail before sending any UART request

### Requirement: Serial exchange behavior
The CLI SHALL send one request frame and read one validated response frame over a selected host serial port.

#### Scenario: Serial port configured
- **WHEN** a user runs any hardware command with `--port`, optional `--baud`, and optional `--timeout`
- **THEN** the CLI SHALL open the port using 8 data bits, no parity, 1 stop bit, the configured baud rate, and the configured timeout

#### Scenario: Response validated
- **WHEN** the FPGA returns a response frame after the command
- **THEN** the CLI SHALL synchronize to `SOF_R=0xAA`, read `LEN`, read the body and checksum bytes, and validate length and checksum before reporting the command result

#### Scenario: NACK reported
- **WHEN** the FPGA returns a response with non-ACK status
- **THEN** the CLI SHALL report the status name, echoed opcode, payload bytes if present, and exit with a non-zero status unless the user explicitly allows NACK responses for diagnostics

### Requirement: Decoded command output
The CLI SHALL display successful responses in command-specific decoded form by default and support machine-readable output for scripts.

#### Scenario: Human output for decoded payload
- **WHEN** a named command returns ACK with the expected payload shape
- **THEN** the CLI SHALL print a concise human-readable result including decoded status, command name, and command-specific payload fields

#### Scenario: Raw frame diagnostics
- **WHEN** a user runs the CLI with verbose output enabled
- **THEN** the CLI SHALL print the raw transmitted request frame and raw received response frame in hexadecimal

#### Scenario: JSON output
- **WHEN** a user requests JSON output
- **THEN** the CLI SHALL print a JSON object that includes success status, numeric status, status name, numeric opcode, opcode name, response payload bytes, and raw response bytes

### Requirement: Raw opcode diagnostics
The CLI SHALL provide a diagnostic mode for sending a user-provided opcode and byte arguments through the normal framed UART protocol.

#### Scenario: Raw request built
- **WHEN** a user runs the raw command with an opcode and optional argument bytes
- **THEN** the CLI SHALL validate each value as a byte and build `[SOF=0x55] [LEN] [OP] [ARGS...] [CHK]` using the same checksum helper as named commands

#### Scenario: Unknown opcode response shown
- **WHEN** the FPGA responds to a raw request whose opcode is not known by the host helper
- **THEN** the CLI SHALL still display the numeric echoed opcode, status name, payload bytes, and raw response frame

### Requirement: Documentation and local checks
The system SHALL document the direct command CLI and provide hardware-free checks for parser and protocol behavior.

#### Scenario: README command examples
- **WHEN** a user reads the host UART section of `README.md`
- **THEN** it SHALL show how to install `pyserial`, list ports, send representative direct commands, enable verbose raw-frame output, and choose JSON output

#### Scenario: Hardware-free CLI checks
- **WHEN** the project test commands are run without an attached FPGA board
- **THEN** they SHALL validate protocol helper examples, Python syntax, CLI help output, and argument validation paths without opening a real serial port
