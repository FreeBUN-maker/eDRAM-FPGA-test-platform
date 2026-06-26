## Why

The FPGA eDRAM test platform needs a deterministic UART protocol between the PC host and the PL-side FPGA logic before RTL command parsing, eDRAM control sequencing, and Python-side test scripts can be implemented consistently.

## What Changes

- Define a byte-oriented UART command frame for PC-to-FPGA requests.
- Define write, read, reset, and status commands at the transaction level instead of exposing every eDRAM signal as an independent host command.
- Define FPGA-to-PC response frames with ACK/NACK status, optional read data, and error codes.
- Define checksum, field ranges, byte order, and malformed-frame behavior.
- Update `doc/FPGA-PC-UART-interface.md` with the initial instruction set contract.

## Non-goals

- This change does not define the detailed eDRAM electrical timing parameters.
- This change does not implement the UART receiver, parser, eDRAM controller FSM, or Python host library.
- This change does not define pin assignments for the FPGA-to-eDRAM interface.

## Capabilities

### New Capabilities
- `uart-host-protocol`: Defines the PC-to-FPGA UART command and response protocol used to control eDRAM read/write transactions.

### Modified Capabilities
- None.

## Impact

- Affects `doc/FPGA-PC-UART-interface.md`.
- Guides future SystemVerilog UART parser and eDRAM command controller modules under `src/rtl`.
- Guides future Python host-side UART control scripts and testbench expectations.
