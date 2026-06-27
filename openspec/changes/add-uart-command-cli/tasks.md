## 1. Shared Host Serial Transport

- [x] 1.1 Add `scripts/uart_serial_transport.py` with lazy `pyserial` import, install hint, serial-port listing, serial config validation, and user-facing exception classes
- [x] 1.2 Move common open/drain/write/read-response logic from `scripts/uart_host_test.py` into the shared transport helper
- [x] 1.3 Keep response synchronization on `SOF_R=0xAA`, length bounds, checksum parsing, timeout diagnostics, and optional raw TX/RX reporting in the shared helper
- [x] 1.4 Update `scripts/uart_host_test.py` to use the shared helper while preserving existing `list`, `basic`/`smoke`, `ping`, `status`, `outputs`, `write-selfcheck`, `full`/`memtest` behavior and messages

## 2. Direct Command CLI

- [x] 2.1 Add `scripts/uart_cmd.py` with `argparse` subcommands and shared serial options for hardware commands
- [x] 2.2 Implement `list` using the shared serial-port discovery helper
- [x] 2.3 Implement `ping`, `reset`, and `status` commands using existing `uart_host_protocol.py` request builders and payload decoders
- [x] 2.4 Implement `write-row`, `read-group`, and `read-row` with row/group/data validation before serial open
- [x] 2.5 Implement `outputs` and `trace` using the existing output snapshot and trace payload decoders
- [x] 2.6 Implement `raw` with byte-validated `--op`, optional `--args`, normal request framing, and `--allow-nack` support for negative diagnostics

## 3. Output, Errors, and Scriptability

- [x] 3.1 Add concise human-readable output for each named command, including decoded status and command-specific payload fields
- [x] 3.2 Add `--verbose` output that prints raw TX and RX frames in hexadecimal without changing command behavior
- [x] 3.3 Add `--json` output with stable fields for success, status, opcode, payload bytes, and raw frame bytes
- [x] 3.4 Ensure ACK payload length mismatches, protocol parse failures, serial timeouts, unexpected opcode echoes, and NACKs exit non-zero with command-specific diagnostics
- [x] 3.5 Ensure invalid arguments fail before opening the serial port for all named commands and raw byte inputs

## 4. Documentation

- [x] 4.1 Update `README.md` to distinguish `scripts/uart_cmd.py` direct command sending from `scripts/uart_host_test.py` validation/self-check flows
- [x] 4.2 Add README examples for `list`, `ping`, `status`, `read-row`, `write-row`, `outputs`, `trace`, and `raw`
- [x] 4.3 Document `--verbose`, `--json`, `--baud`, `--timeout`, and `--allow-nack` behavior
- [x] 4.4 Document expected success output shape and common failure meanings for timeout, malformed response, NACK, and argument validation errors

## 5. Validation

- [x] 5.1 Run `python scripts/uart_host_protocol.py`
- [x] 5.2 Run `python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py scripts/uart_serial_transport.py scripts/uart_cmd.py`
- [x] 5.3 Run `python scripts/uart_cmd.py --help` and representative subcommand `--help` checks
- [x] 5.4 Run invalid-argument checks, including out-of-range row/group, short `write-row --data`, malformed raw args, and confirm they fail before serial open
- [x] 5.5 Run mocked serial exchanges for `ping`, `status`, `read-group`, `read-row`, `outputs`, `trace`, and `raw`
- [x] 5.6 Run `python scripts/uart_host_test.py --help` and a mocked existing test flow to confirm shared transport extraction did not regress the test CLI
- [x] 5.7 If FPGA hardware is available, run `ping`, `status`, and `outputs` through `scripts/uart_cmd.py` against the programmed board and record results
- [x] 5.8 If the eDRAM board is connected and a scratch row is safe to overwrite, run `write-row` followed by `read-row` through `scripts/uart_cmd.py` and record results

## Validation Notes

- 2026-06-27: `python scripts/uart_host_protocol.py` passed.
- 2026-06-27: `python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py scripts/uart_serial_transport.py scripts/uart_cmd.py` passed.
- 2026-06-27: `python scripts/uart_cmd.py --help`, `python scripts/uart_cmd.py raw --help`, `python scripts/uart_cmd.py read-row --help`, and `python scripts/uart_host_test.py --help` passed.
- 2026-06-27: Invalid argument checks for out-of-range row, out-of-range group, short `write-row --data`, oversized raw opcode, and malformed raw args failed before serial open with expected diagnostics.
- 2026-06-27: Mocked serial exchanges exercised `scripts/uart_cmd.py` for `ping`, `status --json`, `read-group`, `read-row`, `outputs`, `trace`, and `raw --allow-nack`; exact TX frames and decoded outputs passed.
- 2026-06-27: Mocked serial exchange exercised `scripts/uart_host_test.py basic` through `RESET`, `PING`, and `STATUS`; it passed after shared transport extraction.
- 2026-06-27: Hardware `uart_cmd.py ping/status/outputs` was not run in this workspace because no FPGA serial port is attached.
- 2026-06-27: Hardware `uart_cmd.py write-row/read-row` was not run in this workspace because no FPGA serial port/eDRAM hardware is attached.
