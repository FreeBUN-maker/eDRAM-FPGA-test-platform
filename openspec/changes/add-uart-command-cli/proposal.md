## Why

The current host tooling is shaped around smoke tests and self-check flows, but bring-up and debug often need a direct way to send one UART protocol command from a shell. A command-focused CLI will let users exercise the existing FPGA UART protocol without hand-building frames or modifying test scripts.

## What Changes

- Add a host-side UART command CLI that sends individual documented protocol commands over a selected serial port.
- Support the current command set: `PING`, `RESET`, `STATUS`, `WRITE_ROW`, `READ_GROUP`, `READ_ROW`, `READ_OUTPUTS`, and `READ_OUTPUT_TRACE`.
- Add a `raw`/diagnostic command path for sending a user-provided opcode and byte arguments while still applying the documented frame and checksum rules.
- Reuse the existing Python protocol helper for opcode constants, request builders, response parsing, checksum handling, output snapshot decoding, and row/group validation.
- Print concise human-readable command results by default, with optional raw TX/RX frame output and machine-readable JSON output for scripts.
- Document usage examples in `README.md` and keep the existing test-oriented CLI available for smoke/self-check flows.

## Non-goals

- Do not change the UART physical settings, request/response frame format, checksum rule, opcodes, status codes, or FPGA RTL behavior.
- Do not replace `scripts/uart_host_test.py`; the new CLI is for direct command sending, while the existing script remains focused on test sequences.
- Do not add a GUI, daemon, REPL, or long-running acquisition application.
- Do not provide cycle-by-cycle raw eDRAM pin control over UART.

## Capabilities

### New Capabilities

- `uart-command-cli`: Host-side command-line interface for sending individual UART protocol commands and displaying validated responses.

### Modified Capabilities

- None.

## Impact

- Affected code: a new command CLI under `scripts/`, plus optional shared serial/formatting helpers if needed to avoid duplicating existing host serial logic.
- Affected documentation: `README.md` usage examples for command-line UART operations.
- Dependencies: continue using `pyserial` for physical serial-port access and the existing project Python environment.
- Affected systems: PC host connected to the AXU5EVB-E PL USB-UART interface at the documented default `115200-8-N-1` settings.
