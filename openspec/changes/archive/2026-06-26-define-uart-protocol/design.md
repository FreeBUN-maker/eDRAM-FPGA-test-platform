## Context

The project uses the PL side of the AXU5EVB-E FPGA board as a UART-controlled eDRAM test platform. The PC host sends commands over UART, and the FPGA receives complete frames, validates them, and drives the eDRAM control FSM.

The eDRAM array is 64 x 64. The FPGA-to-eDRAM interface exposes 6-bit row selection, 3-bit WBL/RBL group selection, 8-bit write data, and 8-bit readback data. The write interface is naturally row-buffer oriented because a full row can be loaded group by group before asserting the selected WWL.

Overall data path:

```text
┌────────────┐   UART bytes   ┌───────────────┐   command   ┌───────────────┐
│ Python PC  │───────────────▶│ UART RX/Parser │────────────▶│ eDRAM Ctrl FSM │
│ host tool  │◀───────────────│ UART TX/Resp   │◀────────────│ result/status  │
└────────────┘   responses    └───────────────┘              └───────┬───────┘
                                                                       │
                                                                       ▼
                                                              ┌────────────────┐
                                                              │ eDRAM test chip │
                                                              └────────────────┘
```

## Goals / Non-Goals

**Goals:**

- Define a byte-oriented UART frame that is simple to parse in SystemVerilog.
- Define transaction-level commands for row write, group read, row read, reset, status, and connectivity testing.
- Define ACK/NACK responses so the Python host can know whether a command completed.
- Define checksum and argument validation rules.
- Keep the protocol extensible without requiring an immediate redesign.

**Non-Goals:**

- Defining exact eDRAM pulse widths and setup/hold timing.
- Defining the final Python host API.
- Implementing UART RX/TX, command parser, or eDRAM controller RTL.
- Supporting high-throughput burst streaming in the first revision.

## Decisions

### Decision: Use transaction-level commands

The PC sends operations such as `WRITE_ROW` and `READ_GROUP`; the FPGA generates the detailed eDRAM signal sequence internally.

Alternative considered: expose every eDRAM signal as an individual UART command. This was rejected for the normal path because UART timing is too slow and non-deterministic for direct signal sequencing from the PC. Low-level signal poking can be added later as a debug-only extension.

### Decision: Use variable-length byte frames

Frame format:

```text
Request : [SOF=0x55] [LEN] [OP] [ARGS...] [CHK]
Response: [SOF=0xAA] [LEN] [STATUS] [OP_ECHO] [DATA...] [CHK]
```

`LEN` counts the bytes after `LEN` and before `CHK`. `CHK` is the XOR of `LEN` and the following `LEN` bytes. This keeps fixed parsing rules while allowing both short commands and full-row writes.

### Decision: Make full-row write the primary write command

`WRITE_ROW` carries one row address and eight data bytes, one byte per WBL group. This matches the current eDRAM write sequence: load WBL groups, then assert the selected WWL.

Alternative considered: `WRITE_GROUP(row, group, data)`. This is convenient for software but may be unsafe if asserting WWL writes all WBL lanes. It can be added later only after the hardware semantics of partial-row write are confirmed.

### Decision: Return explicit ACK/NACK status

Every validly framed request produces one response. `STATUS=0x00` is ACK/success; non-zero status values are NACK/error codes. Read commands return data only when status is ACK.

### Timing diagram

```text
PC                         FPGA UART Parser          eDRAM Ctrl FSM
│                                │                         │
│  SOF LEN OP ARGS CHK           │                         │
├───────────────────────────────▶│                         │
│                                │ validate SOF/LEN/CHK    │
│                                ├────────────────────────▶│
│                                │                         │ execute command
│                                │                         │ capture result
│  SOF_R LEN STATUS OP DATA CHK  │                         │
│◀───────────────────────────────┤◀────────────────────────┤
│                                │                         │
```

## Risks / Trade-offs

- Full-row writes are less convenient than single-cell writes -> The first revision prioritizes hardware correctness; a host helper can build row payloads.
- XOR checksum detects many common byte errors but not all multi-bit errors -> Upgrade to CRC-8 later if error detection becomes important.
- Variable-length frames need a small parser FSM -> The parser remains simple because `LEN` is bounded and every command has fixed expected argument lengths.
- No streaming mode in v1 -> Add burst commands only after the basic read/write path is verified.

## Migration Plan

1. Document the v1 UART protocol in `doc/FPGA-PC-UART-interface.md`.
2. Implement RTL parser and response generator against the documented frame format.
3. Implement Python host helpers that build frames and check responses.
4. Add simulation test vectors for valid frames, bad checksum, bad length, bad opcode, and out-of-range arguments.

Rollback is straightforward because this is an initial protocol definition; no existing RTL or host tool depends on a previous stable protocol.

## Open Questions

- Exact UART baud rate can remain configurable, but the documentation should specify a default.
- Exact eDRAM pulse widths and read latency must be defined before implementing the eDRAM controller FSM.
- Whether a safe partial-row write exists depends on the eDRAM board behavior and should be confirmed before adding a `WRITE_GROUP` command.

## Modules to be revised

- `doc/FPGA-PC-UART-interface.md`: Add the protocol contract.
- Future `src/rtl` modules: UART receiver, frame parser, command dispatcher, response encoder, eDRAM controller FSM.
- Future Python host scripts: frame builder, response parser, command helpers.
