## Why

`README.md` now requires a self-check path that samples the eDRAM control/data signals at the FPGA output side and returns them to the PC over UART. The current design can execute UART eDRAM transactions and return eDRAM read data, but it does not expose the driven output-port values for host-side comparison against the intended command payloads.

## What Changes

- Add a UART-readable output-port snapshot command that returns the current FPGA-driven eDRAM output signals (`LOAD`, `READ`, `EN-WWL`, `EN-RWL`, `WG`, `RG`, `DIN`, `A`, and `W`) in a documented byte layout.
- Capture the snapshot from the same nets that drive `edram_pl_top` / `edram_pl_board_top` external output ports, so host checks observe the actual top-level output values rather than only internal command arguments.
- Extend the RTL command dispatcher/protocol constants and top-level wiring needed to serve the snapshot command without starting an eDRAM transaction.
- Update host UART protocol/test code so PC-side tests can request the snapshot and compare it with the host's expected idle/write/read intent.
- Update Vivado source/configuration metadata and Tcl source handling if the implementation adds a reusable snapshot/packing RTL module.
- Add simulation coverage for the new command and host-side protocol helper coverage for the new frame/payload layout.

## Non-goals

- Do not replace the existing transaction-level UART interface with per-cycle raw pin control.
- Do not change existing opcode semantics, response frame format, checksum rule, UART baud defaults, or eDRAM timing parameters.
- Do not add new board pins or require a physical loopback from expansion connector pins back into FPGA inputs.
- Do not make the host test prove analog signal integrity on the external connector; it verifies the digital values driven onto the top-level output nets.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `uart-host-protocol`: Add a documented output-port snapshot command and host-visible response payload layout.
- `pl-only-control-plane`: Add PL-only RTL behavior that snapshots the driven eDRAM output-port nets and returns them over UART without PS involvement.
- `vivado-config-json`: Keep Vivado source metadata aligned if the snapshot logic is implemented as an added RTL source file.
- `vivado-project-mode-tcl`: Keep the Vivado Tcl source helper aligned so project-mode builds compile the added snapshot RTL.

## Impact

- Affected RTL: `src/rtl/edram_pkg.sv`, `src/rtl/cmd_dispatcher.sv`, `src/rtl/edram_pl_top.sv`, possibly a new snapshot packing module under `src/rtl/`, and board-top wiring only if needed.
- Affected host code: `scripts/uart_host_protocol.py`, `scripts/uart_host_test.py`, plus matching simulation helper constants in `sim/tb/protocol.py`.
- Affected tests: cocotb tests for `edram_pl_top` and Python protocol/CLI checks.
- Affected Vivado flow: `src/vivado/sources.tcl` and `src/vivado/config.json` source lists if a new RTL file is introduced; project Tcl validation should continue to load the complete source set.
