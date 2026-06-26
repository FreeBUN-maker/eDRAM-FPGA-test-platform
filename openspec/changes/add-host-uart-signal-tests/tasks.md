## 1. Protocol Helper

- [x] 1.1 Add `scripts/uart_host_protocol.py` with SOF, opcode, status, baud-rate, and row/group constants aligned with `doc/FPGA-PC-UART-interface.md`
- [x] 1.2 Implement XOR checksum, generic request builder, and command builders for `PING`, `RESET`, `STATUS`, `WRITE_ROW`, `READ_GROUP`, and `READ_ROW`
- [x] 1.3 Implement response parsing with SOF, length, checksum, status, opcode echo, payload, and raw-frame reporting
- [x] 1.4 Add readable opcode/status name helpers and a protocol-specific exception type for diagnostics
- [x] 1.5 Add a hardware-free helper self-test that checks the documented frame examples

## 2. Serial CLI

- [x] 2.1 Add `scripts/uart_host_test.py` with `argparse` subcommands for `list`, `ping`, `status`, `smoke`, and `memtest`
- [x] 2.2 Implement lazy `pyserial` import with an actionable install hint when the dependency is missing
- [x] 2.3 Implement serial open/drain/write/read helpers using 8 data bits, no parity, 1 stop bit, configurable baud, and configurable timeout
- [x] 2.4 Implement response synchronization on `0xAA`, response frame validation, command echo checking, and verbose raw-byte logging
- [x] 2.5 Ensure every failing hardware command exits non-zero with a specific timeout, protocol, NACK, or mismatch message

## 3. Host Tests

- [x] 3.1 Implement `ping` with configurable repeat count and validation of ACK payload `[0xA5]`
- [x] 3.2 Implement `status` with decoded busy bit and last-error status output
- [x] 3.3 Implement `smoke` as `RESET`, `PING`, and `STATUS` with clear pass/fail summary
- [x] 3.4 Implement `memtest` with explicit row selection, generated pattern options, `WRITE_ROW`, `READ_ROW`, and group-by-group comparison
- [x] 3.5 Reject out-of-range rows/groups and malformed byte patterns before sending any UART request

## 4. Documentation

- [x] 4.1 Update `README.md` with dependency installation instructions for `pyserial`
- [x] 4.2 Add serial-port discovery guidance for Linux and Windows hosts
- [x] 4.3 Add documented commands for protocol self-test, `list`, `smoke`, `ping`, `status`, and `memtest`
- [x] 4.4 Document recommended bring-up order: program bitstream, run smoke test, then run memory test only when the eDRAM board is connected and the selected row may be overwritten
- [x] 4.5 Document expected success output shape and common failure meanings for timeout, NACK, and readback mismatch

## 5. Validation

- [x] 5.1 Run the protocol helper self-test without hardware
- [x] 5.2 Run a Python syntax check for the new scripts
- [x] 5.3 If `pyserial` is installed, run the `list` subcommand without requiring FPGA hardware
- [x] 5.4 When FPGA hardware is available, run `smoke` against the programmed board and record the command/result
- [ ] 5.5 When the eDRAM board is connected and a scratch row is safe to overwrite, run `memtest` and record the command/result

## Validation Notes

- 2026-06-26: `python scripts/uart_host_protocol.py` passed.
- 2026-06-26: `python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py` passed.
- 2026-06-26: `python scripts/uart_host_test.py --help` passed and shows `list`, `basic`, `smoke`, `ping`, `status`, `full`, and `memtest`.
- 2026-06-26: `python scripts/uart_host_test.py full --port dummy --row 64` failed before serial open with the expected row-range error.
- 2026-06-26: `python scripts/uart_host_test.py full --port dummy --row 0 --data "00 11 22"` failed before serial open with the expected data-length error.
- 2026-06-26: A `PYTHONPATH=scripts python - <<'PY' ...` mock serial run exercised `full` mode through `RESET`, `PING`, `STATUS`, `WRITE_ROW`, `READ_GROUP`, `READ_ROW`, and final `STATUS`; it passed.
- 2026-06-26: `python -c "import serial; print(serial.__version__)"` failed because `pyserial` is not installed in this environment; `python scripts/uart_host_test.py list` returned the expected install hint.
- 2026-06-26: Hardware `basic`/`smoke` and `full`/`memtest` runs were not executed here because no FPGA serial port/eDRAM hardware is available in this workspace.
- 2026-06-26: User reported that `list`/5.3 and board-level `smoke`/5.4 have passed outside this workspace. eDRAM-connected `memtest`/5.5 remains pending.
