## Context

The current PL-only design already accepts UART commands, drives eDRAM output pins, and returns command responses. However, the only data returned from the eDRAM side is `P[7:0]` sampled during read commands. There is no UART-visible path that reports the FPGA-driven output nets (`LOAD`, `READ`, `EN-WWL`, `EN-RWL`, `WG`, `RG`, `DIN`, `A`, and `W`) back to the PC.

The README requirement is specifically about self-checking the driven output signals. A post-transaction "current output" read is not enough for write-signal validation because the controller normally returns the pins to idle before the UART ACK reaches the host. The design therefore needs both a live snapshot and a small trace of recently driven output-port values.

### Overall system impact

```text
Before:

  PC UART -> uart_rx -> parser -> dispatcher -> eDRAM FSM -> eDRAM output ports
                                      |
                                      +-> response encoder -> uart_tx

After:

  PC UART -> uart_rx -> parser -> dispatcher -> eDRAM FSM -> output drive nets -> eDRAM ports
                                      |                         |
                                      |                         v
                                      |                  output snapshot/trace
                                      |                         |
                                      +<------------------------+
                                      |
                                      +-> response encoder -> uart_tx
```

### Modules to be revised

```text
src/rtl/
  edram_pkg.sv                 add READ_OUTPUTS / READ_OUTPUT_TRACE opcodes and lengths
  edram_output_snapshot.sv     new live snapshot + trace recorder/packer
  cmd_dispatcher.sv            serve the new snapshot/trace commands
  edram_pl_top.sv              route output drive nets into the snapshot module

scripts/
  uart_host_protocol.py        add frame builders and snapshot decode helpers
  uart_host_test.py            add output snapshot and write-signal self-check flows

sim/tb/
  protocol.py                  mirror new opcodes/builders for cocotb tests
  test_edram_pl_top.py         verify output snapshot and write trace over UART

src/vivado/
  sources.tcl                  include any new RTL source
  config.json                  keep source metadata aligned with Vivado Tcl
```

## Goals / Non-Goals

**Goals:**

- Let the PC read a packed snapshot of the eDRAM output-port values over the existing UART response path.
- Preserve a queryable trace of the latest eDRAM transaction's active output snapshots so `WRITE_ROW` output intent can be checked after the transaction completes.
- Keep the new UART payloads small enough for the current response encoder data path.
- Update host test code so a user can run an output idle check and a write-signal self-check from the PC.
- Keep Vivado project Tcl/config source lists synchronized with any added RTL file.

**Non-Goals:**

- Do not add physical loopback pins or new top-level external ports.
- Do not stream every clock cycle over UART.
- Do not change existing command opcodes, payloads, checksums, or UART physical settings.
- Do not make this an analog board-level signal-integrity measurement.

## Decisions

### Decision: Add `READ_OUTPUTS` for live output-port snapshots

Add `OP_READ_OUTPUTS = 0x06` with no request payload. The ACK response payload is five bytes:

```text
S0 bit0    edram_load_n_o
S0 bit1    edram_read_n_o
S0 bit2    edram_en_wwl_n_o
S0 bit3    edram_en_rwl_n_o
S0 bit7:4  0

S1 bit2:0  edram_wg_o[2:0]
S1 bit5:3  edram_rg_o[2:0]
S1 bit7:6  0

S2         edram_din_o[7:0]
S3 bit5:0  edram_a_o[5:0]
S3 bit7:6  0
S4 bit5:0  edram_w_o[5:0]
S4 bit7:6  0
```

Rationale: five bytes cover every FPGA output currently driven toward the eDRAM board while leaving the response encoder's existing 8-byte payload limit intact.

Alternative considered: extend `STATUS` with these fields. Keeping a separate opcode avoids changing existing `STATUS` payload shape and host scripts.

### Decision: Add `READ_OUTPUT_TRACE` for post-transaction self-check

Add `OP_READ_OUTPUT_TRACE = 0x07` with request payload `[INDEX]`. The ACK response payload is:

```text
[COUNT] [INDEX] [S0] [S1] [S2] [S3] [S4]
```

`COUNT` is the number of valid records captured for the latest transaction, capped by the RTL trace depth. `INDEX` selects one record. If `INDEX >= COUNT`, the dispatcher returns `NACK_BAD_ARG`.

Rationale: this gives the PC a way to inspect write-time output states after `WRITE_ROW` has completed. A `WRITE_ROW` self-check can read records until the expected group-load snapshots and row-write snapshot have been validated.

Alternative considered: return the full trace in one UART response. That would require enlarging the response encoder and host parser for a single debug feature. Indexed reads keep the protocol simple and bounded.

### Decision: Capture from output drive nets, not command arguments

`edram_pl_top` should introduce local drive nets for every eDRAM output. The eDRAM FSM drives those nets, the top-level ports are assigned from those same nets, and `edram_output_snapshot` samples those nets.

Rationale: the PC must see what the FPGA actually drove at the output boundary. Reconstructing expected values inside the dispatcher would only verify command parsing, not top-level output wiring.

Alternative considered: sample inside `edram_ctrl_fsm`. That is closer to the state machine but misses top-level wiring mistakes between the FSM and output ports.

### Decision: Record compact active snapshots during each eDRAM transaction

The snapshot module should clear the trace when a new eDRAM request is accepted, then append a record when the packed output snapshot changes while any active-low control is asserted (`LOAD`, `READ`, `EN-WWL`, or `EN-RWL` low). The default trace depth should be at least 16 records, enough for a full `WRITE_ROW` sequence of eight group-load records plus the row-write record and read command debug records.

Rationale: recording only active, changed snapshots keeps the trace useful without streaming idle cycles.

Alternative considered: record one entry per clock. That would overflow quickly and make UART-side validation dependent on timing parameters.

### Decision: Add host CLI coverage instead of relying on raw frame tools

Extend the host protocol helper with snapshot builders and decode helpers, and extend the CLI with:

```text
python scripts/uart_host_test.py outputs --port /dev/ttyUSB0
python scripts/uart_host_test.py write-selfcheck --port /dev/ttyUSB0 --row 0 --pattern walking
```

`outputs` should decode and print the live snapshot. `write-selfcheck` should send `WRITE_ROW`, query trace records, and compare observed `WG`, `DIN`, and row/address/control values against the requested row and pattern.

Rationale: the user requirement is a PC-side check. A raw UART opcode is technically enough but too tedious for bring-up.

Alternative considered: add only protocol helpers and leave the user to script validation manually. That would satisfy the RTL path but not the requested synchronized UART test code.

### Timing diagram

```text
PC host                    dispatcher/FSM            output snapshot trace
   |                            |                              |
   | WRITE_ROW(row,data) -----> |                              |
   |                            | request accepted             |
   |                            |----------------------------->| clear trace
   |                            | LOAD group 0, DIN D0         |
   |                            |----------------------------->| record index 0
   |                            | LOAD group 1, DIN D1         |
   |                            |----------------------------->| record index 1
   |                            | ...                          |
   |                            | EN-WWL row A                 |
   |                            |----------------------------->| record row-write
   |<------ ACK WRITE_ROW ------|                              |
   |                            |                              |
   | READ_OUTPUT_TRACE(0) ----> |----------------------------->| select index 0
   |<-- COUNT,0,SNAPSHOT -------|                              |
   | READ_OUTPUT_TRACE(1) ----> |----------------------------->| select index 1
   |<-- COUNT,1,SNAPSHOT -------|                              |
   | ... compare against host intent ...                       |
```

## Risks / Trade-offs

- [Risk] The trace is a digital observation of FPGA output nets, not a board-level electrical loopback. -> Mitigation: document the scope clearly and avoid claiming signal-integrity validation.
- [Risk] Trace capture could miss a short output state if implemented after state updates incorrectly. -> Mitigation: capture synchronously every PL clock while active controls are asserted and cover the expected write sequence in cocotb.
- [Risk] Existing response encoder data width is limited to 8 bytes. -> Mitigation: keep live snapshots at 5 bytes and trace responses at 7 bytes.
- [Risk] Host self-check may overwrite an eDRAM row. -> Mitigation: require explicit `--row` and document that the selected row must be safe to drive.
- [Risk] Adding a new RTL file can break Vivado source ordering. -> Mitigation: update both `sources.tcl` and `config.json`, then run the existing source/config validation checks.

## Migration Plan

1. Add the output snapshot RTL module and integrate it into `edram_pl_top`.
2. Add new opcode constants, expected lengths, dispatcher response paths, and simulation helpers.
3. Update host protocol/test scripts and README usage examples for `outputs` and `write-selfcheck`.
4. Update Vivado `sources.tcl` and `config.json` source lists.
5. Run Python protocol checks, cocotb tests for the top-level UART path, and Vivado/static source-list validation.

Rollback is limited to removing the new opcodes, snapshot module, host CLI commands, documentation, and source-list entries because no existing command behavior is changed.

## Open Questions

- None for the proposal stage. The exact trace depth can remain a parameter as long as the default can capture a full write self-check sequence.
