## 1. Protocol and RTL Interfaces

- [x] 1.1 Add `OP_READ_OUTPUTS=0x06` and `OP_READ_OUTPUT_TRACE=0x07` to `src/rtl/edram_pkg.sv`
- [x] 1.2 Update `uart_expected_len()` for the new no-payload and one-byte-payload commands
- [x] 1.3 Add packed snapshot width/layout constants or helper comments that match the spec byte layout

## 2. Output Snapshot RTL

- [x] 2.1 Add `src/rtl/edram_output_snapshot.sv` to pack live eDRAM output drive nets into five snapshot bytes
- [x] 2.2 Implement trace clear on accepted eDRAM transaction start and reset/soft-reset handling
- [x] 2.3 Implement active changed-snapshot trace capture with a default depth sufficient for a full `WRITE_ROW` sequence
- [x] 2.4 Implement trace index selection, count reporting, and invalid-index indication for dispatcher use

## 3. Top-Level and Dispatcher Integration

- [x] 3.1 Route eDRAM controller outputs through local drive nets in `edram_pl_top.sv` before assigning top-level output ports
- [x] 3.2 Instantiate `edram_output_snapshot` from `edram_pl_top.sv` and connect it to the same output drive nets
- [x] 3.3 Extend `cmd_dispatcher.sv` ports to receive live snapshot data, trace count/data, and drive trace index selection
- [x] 3.4 Add `READ_OUTPUTS` response handling with a five-byte ACK payload and no eDRAM request
- [x] 3.5 Add `READ_OUTPUT_TRACE` response handling with `[COUNT] [INDEX] [snapshot]` ACK payload and `NACK_BAD_ARG` for invalid indexes
- [x] 3.6 Ensure `RESET` clears or invalidates stale trace records and restores the idle live snapshot

## 4. Host UART Test Code

- [x] 4.1 Add new opcode constants, frame builders, and snapshot decode helpers to `scripts/uart_host_protocol.py`
- [x] 4.2 Add protocol self-tests for `READ_OUTPUTS`, `READ_OUTPUT_TRACE`, snapshot packing/decoding, and invalid frame parsing as applicable
- [x] 4.3 Add an `outputs` CLI subcommand to `scripts/uart_host_test.py` that reads and prints the live output snapshot
- [x] 4.4 Add a `write-selfcheck` CLI flow that sends `WRITE_ROW`, reads output trace records, and compares observed `WG`, `DIN`, and row/address/control values with the requested row/pattern
- [x] 4.5 Keep existing `basic`/`smoke`/`full`/`memtest` behavior compatible with the new protocol constants

## 5. Simulation and Testbench Updates

- [x] 5.1 Mirror new opcodes and frame builders in `sim/tb/protocol.py`
- [x] 5.2 Add cocotb coverage proving `READ_OUTPUTS` returns the reset/idle output snapshot
- [x] 5.3 Add cocotb coverage proving a `WRITE_ROW` transaction produces queryable trace records for each group and the row-write address
- [x] 5.4 Add cocotb coverage for invalid `READ_OUTPUT_TRACE` indexes returning `NACK_BAD_ARG`

## 6. Vivado and Documentation

- [x] 6.1 Add `src/rtl/edram_output_snapshot.sv` to `src/vivado/sources.tcl` in compile-safe order
- [x] 6.2 Add `src/rtl/edram_output_snapshot.sv` to `src/vivado/config.json` in matching source order
- [x] 6.3 Update README or UART protocol documentation with the new output snapshot commands and host test examples
- [x] 6.4 Confirm no XDC pin changes are required because no external top-level ports are added

## 7. Validation

- [x] 7.1 Run `python scripts/uart_host_protocol.py`
- [x] 7.2 Run `python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py`
- [x] 7.3 Run relevant cocotb top-level UART tests for `edram_pl_top`
- [x] 7.4 Run existing Vivado/static source-list validation for `src/vivado/sources.tcl` and `src/vivado/config.json`
- [x] 7.5 If FPGA hardware is available, run `outputs` and `write-selfcheck` against the programmed board and record results

## Validation Notes

- 2026-06-27: `python scripts/uart_host_protocol.py` passed.
- 2026-06-27: `python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py` passed.
- 2026-06-27: `conda run -n track4-fa python sim/tb/run_cocotb.py` passed; `test_edram_pl_top` includes `READ_OUTPUTS`, `READ_OUTPUT_TRACE`, and invalid trace-index coverage.
- 2026-06-27: `python -m json.tool src/vivado/config.json >/dev/null` passed.
- 2026-06-27: `python scripts/check_vivado_explicit_input_nets.py` passed, checking 12 SystemVerilog files.
- 2026-06-27: `tclsh` source helper check resolved 12 RTL source files from `src/vivado/sources.tcl`.
- 2026-06-27: Config source-order check confirmed `src/rtl/edram_output_snapshot.sv` appears before `src/rtl/edram_pl_top.sv`.
- 2026-06-27: `python scripts/uart_host_test.py --help` passed.
- 2026-06-27: A mocked serial run exercised `outputs` and `write-selfcheck` host flows without hardware and passed.
- 2026-06-27: Hardware `outputs` and `write-selfcheck` were not run in this workspace because no FPGA serial port is attached.
