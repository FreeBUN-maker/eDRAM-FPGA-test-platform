## Context

The FPGA UART protocol is already defined in `doc/FPGA-PC-UART-interface.md` and mirrored by RTL constants in `src/rtl/edram_pkg.sv`. The board bitstream flow is now working, so host-side bring-up needs a repeatable way to verify that bytes sent by a PC reach the PL UART receiver, are dispatched by the FPGA, and return through the PL UART transmitter.

Current useful facts:

- The physical UART setting is `115200-8-N-1`.
- Request frames use `SOF=0x55`, response frames use `SOF_R=0xAA`, and both use XOR checksums over `[LEN, body...]`.
- `PING`, `RESET`, and `STATUS` do not require the external eDRAM contents to be meaningful.
- `WRITE_ROW`, `READ_GROUP`, and `READ_ROW` exercise the full eDRAM command path after the external eDRAM board is connected.
- `sim/tb/protocol.py` already validates protocol examples for simulation, but host bring-up still needs serial-port I/O, CLI arguments, timeout handling, and user-friendly diagnostics.

### Overall system impact

```text
Before this change:

  README/Vivado flow -> programmed FPGA
        |
        v
  Manual serial testing or ad hoc scripts

After this change:

  README/Vivado flow -> programmed FPGA
        |
        v
  scripts/uart_host_test.py
        |
        +-- scripts/uart_host_protocol.py
        |
        v
  pyserial -> PC serial port -> PL USB-UART pins -> FPGA UART protocol
```

The RTL, Vivado Tcl, XDC, and protocol documentation remain the source of truth for hardware behavior. The new scripts only add host-side test access.

### Host test block diagram

```text
+----------------------------- PC host -----------------------------+
|                                                                    |
|  +----------------------+       +-------------------------------+  |
|  | uart_host_test.py    |       | uart_host_protocol.py         |  |
|  | CLI args/subcommands |------>| constants/builders/parser     |  |
|  +----------------------+       +-------------------------------+  |
|              |                                      ^              |
|              v                                      |              |
|  +----------------------+       response validation |              |
|  | pyserial Serial      |---------------------------+              |
|  +----------------------+                                          |
+--------------|-----------------------------------------------------+
               |
               | 115200-8-N-1
               v
+--------------|---------------- FPGA PL ----------------------------+
|              v                                                     |
|        uart_rx -> frame_parser -> cmd_dispatcher -> resp_encoder   |
|              ^                                      |              |
|              +--------------- uart_tx <-------------+              |
+--------------------------------------------------------------------+
```

### Request/response timing diagram

```text
PC host                         FPGA PL
   |                               |
   | open serial 115200-8-N-1      |
   | drain stale input             |
   |                               |
   | 55 LEN OP ARGS CHK ---------->|
   |                               | parse SOF/LEN/body/checksum
   |                               | execute command
   |<---------- AA LEN ST OP DATA CHK
   | read SOF, LEN, body, CHK      |
   | validate length/checksum      |
   | validate OP_ECHO/status/data  |
   | print PASS/FAIL and exit code |
```

## Goals / Non-Goals

**Goals:**

- Add host-side Python scripts that can verify the physical UART path after a bitstream is programmed.
- Keep frame building and response parsing in one reusable helper module.
- Provide a fast smoke test for `PING`, `RESET`, and `STATUS`.
- Provide an optional eDRAM transaction test for `WRITE_ROW`, `READ_GROUP`, and `READ_ROW`.
- Produce clear diagnostics for timeout, bad SOF, bad length, bad checksum, unexpected opcode echo, NACK status, and readback mismatch.
- Document install and run commands in `README.md`.

**Non-Goals:**

- Do not change the protocol, RTL, Vivado flow, constraints, or eDRAM timing.
- Do not add raw pin toggling over UART.
- Do not require hardware access for protocol frame unit/self-tests.
- Do not make the CLI a production data-logging application.

## Decisions

### Decision: Add a dedicated host protocol helper under `scripts/`

Create a small helper module, tentatively `scripts/uart_host_protocol.py`, with:

- protocol constants for SOF, opcodes, status codes, and default baud;
- `checksum(data)`;
- request builders for `ping`, `reset`, `status`, `write_row`, `read_group`, and `read_row`;
- a `Response` data class or named tuple containing `status`, `op`, `data`, and raw bytes;
- `parse_response(frame)` with length and checksum validation;
- status/opcode name helpers for readable CLI output;
- a self-test entry point using the documented example frames.

Rationale: host scripts need the same frame rules in multiple commands. Keeping them in one helper avoids slightly different checksum, length, or status-name logic across scripts.

Alternative considered: import `sim/tb/protocol.py` directly. That file is useful simulation support, but the host CLI should not depend on testbench paths or accidentally inherit cocotb/test-specific assumptions. The implementation may still compare against its examples or reuse logic carefully if the structure remains clean.

### Decision: Use one CLI with subcommands rather than several near-duplicate scripts

Create `scripts/uart_host_test.py` as the primary executable. It should use `argparse` and support:

```text
python scripts/uart_host_test.py list
python scripts/uart_host_test.py smoke --port COM7
python scripts/uart_host_test.py ping --port COM7 --count 10
python scripts/uart_host_test.py status --port COM7
python scripts/uart_host_test.py memtest --port COM7 --row 0 --pattern walking
```

Common options:

```text
--port PATH_OR_COM_NAME
--baud 115200
--timeout 1.0
--verbose
```

Rationale: a single CLI keeps serial handling, logging, exit codes, and README examples consistent while still exposing separate bring-up flows.

Alternative considered: separate `ping_uart.py`, `status_uart.py`, and `memtest_uart.py` scripts. That is quick to write, but it tends to duplicate serial timeout and parsing behavior. One CLI with subcommands still satisfies the need for scripts while keeping the implementation maintainable.

### Decision: Implement strict framed serial reads with resynchronization

The transport layer should:

1. open the selected serial port with `bytesize=8`, `parity=none`, `stopbits=1`, and configurable baud/timeout;
2. drain stale input before each test sequence unless `--no-drain` is later added;
3. write exactly one request frame per transaction;
4. read until `0xAA` or timeout;
5. read `LEN`, then `LEN + 1` more bytes for body and checksum;
6. parse and validate the full response frame;
7. reject unexpected `OP_ECHO`, non-ACK status, and unexpected payload length.

Rationale: byte streams can contain stale bytes from reset or previous attempts. Synchronizing on `SOF_R` makes the script more useful during bring-up while still failing on malformed complete frames.

Alternative considered: fixed-size reads based only on the command. That works for ideal responses but produces confusing failures when a stale byte or partial frame is present.

### Decision: Separate connectivity smoke tests from eDRAM read/write tests

`smoke` should run without depending on eDRAM array contents:

```text
RESET  -> expect ACK
PING   -> expect ACK payload [0xA5]
STATUS -> expect ACK payload [STATE, LAST_ERR]
```

`memtest` should be opt-in because it requires the eDRAM board, stable timing, and a selected row that is safe to overwrite. It should:

1. generate an 8-byte pattern for the selected row;
2. send `WRITE_ROW`;
3. read back with `READ_ROW` and compare all groups;
4. optionally read selected groups with `READ_GROUP` for narrower diagnostics.

Rationale: bring-up often starts with only the FPGA board and UART adapter. A smoke test that avoids memory assumptions gives quick signal-path confidence before debugging eDRAM timing.

Alternative considered: always run memory write/read after ping. That could make a good UART path look broken when the external eDRAM path is not yet connected or calibrated.

### Decision: Keep dependencies minimal and explicit

Use `pyserial` for physical serial access. If `serial` cannot be imported, the CLI should print an actionable install hint such as:

```text
python -m pip install pyserial
```

The protocol helper self-test should not require `pyserial`, so frame-format checks can run in a local or CI environment without hardware.

Alternative considered: use only OS-specific serial APIs. That would avoid a dependency but would make Windows/Linux handling harder and less reliable.

### Modules to be revised

```text
scripts/
  uart_host_protocol.py    new reusable protocol helper
  uart_host_test.py        new CLI for list, smoke, ping, status, memtest

README.md                 add host UART test usage section

optional local checks:
  sim/tb/protocol.py       no required change; compare behavior or avoid conflict
```

## Risks / Trade-offs

- [Risk] The host cannot automatically know the correct serial port. -> Mitigation: add a `list` subcommand and require `--port` for tests.
- [Risk] A good UART path may fail `memtest` because the eDRAM board, timing, or row contents are not stable. -> Mitigation: keep `smoke` as the first recommended test and document `memtest` as the full path check.
- [Risk] Serial timeouts vary by USB-UART adapter and host OS. -> Mitigation: make `--timeout` configurable and include received raw bytes in verbose failure output.
- [Risk] Duplicate protocol constants may drift from RTL. -> Mitigation: include self-tests using documented examples and keep constants visibly aligned with `edram_pkg.sv` and `doc/FPGA-PC-UART-interface.md`.
- [Risk] `pyserial` may be missing in the existing conda environment. -> Mitigation: fail with a dependency hint and document installation in `README.md`.

## Migration Plan

1. Add the helper and CLI scripts.
2. Add protocol self-tests that run without hardware.
3. Document dependency installation and hardware run commands in `README.md`.
4. Run local self-tests in the project Python environment.
5. Run hardware smoke tests on the programmed board when the serial port is available.

Rollback is limited to removing the new host scripts and README section because no RTL or Vivado behavior changes are introduced.

## Open Questions

- Which serial port name should be used in the README examples for the user's current host OS? The documentation can show both Linux and Windows examples.
- Should the first `memtest` default row be `0` or should the user always provide `--row` to make overwrites explicit? The safer implementation is to require `--row` for memory tests.
