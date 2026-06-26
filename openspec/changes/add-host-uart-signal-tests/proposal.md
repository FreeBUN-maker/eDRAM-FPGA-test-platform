## Why

Vivado flow is now passing, so the next bring-up risk is whether the programmed FPGA board can actually receive host UART requests and return valid responses. A small host-side Python toolset will make the UART path testable from a PC without manually composing frames or interpreting raw serial bytes.

## What Changes

- Add Python host scripts for opening a serial port, building documented UART request frames, reading and validating FPGA response frames, and reporting clear pass/fail diagnostics.
- Provide connectivity tests for `PING`, `RESET`, and `STATUS` so the basic PC-to-FPGA and FPGA-to-PC UART path can be checked immediately after bitstream programming.
- Provide optional eDRAM transaction tests using `WRITE_ROW`, `READ_GROUP`, and `READ_ROW` to verify the full command path once the external eDRAM board is connected and stable.
- Add a small reusable protocol helper so frame constants, checksum rules, command builders, and response parsing are not duplicated across scripts.
- Document the host-side run commands, serial-port arguments, default baud rate, and expected output in `README.md`.

## Non-goals

- Do not change the FPGA UART frame format, opcodes, status codes, or checksum semantics.
- Do not change RTL modules, Vivado project Tcl, board constraints, or eDRAM timing parameters.
- Do not add a GUI or long-running production data-acquisition application.
- Do not require raw per-signal UART control of eDRAM pins; scripts use the existing transaction-level protocol.

## Capabilities

### New Capabilities

- `host-uart-signal-tests`: Host-side Python tools for validating the UART signal path and documented command/response protocol against programmed FPGA hardware.

### Modified Capabilities

- None.

## Impact

- Affected code: new Python files under `scripts/` or a small host helper package under `scripts/`.
- Affected documentation: `README.md` host UART test section with install and run examples.
- Dependencies: `pyserial` for physical serial-port access, using the existing project Python/conda environment where possible.
- Affected systems: PC host connected to the AXU5EVB-E PL USB-UART interface at the documented default `115200-8-N-1` settings.
