## Context

The UART protocol is already documented in `doc/FPGA-PC-UART-interface.md` and implemented in the FPGA PL path. Host Python support currently includes:

- `scripts/uart_host_protocol.py`: request builders, response parser, opcode/status names, row/group validation, output snapshot decoding, and protocol self-test examples.
- `scripts/uart_host_test.py`: test-oriented flows such as `basic`, `full`, `outputs`, and `write-selfcheck`.

That tooling is good for validation, but it is awkward for one-off command sending during board bring-up. Users should be able to run commands like `ping`, `read-row`, `write-row`, `outputs`, or `raw` directly from the shell and inspect the immediate response.

### Overall System Impact

```text
Before this change:

  user shell
      |
      v
  scripts/uart_host_test.py test flows
      |
      v
  uart_host_protocol.py -> pyserial -> FPGA UART protocol

After this change:

  user shell
      |
      +--> scripts/uart_host_test.py test/self-check flows
      |
      +--> scripts/uart_cmd.py direct command sender
                |
                v
          uart_host_protocol.py + shared serial helpers
                |
                v
          pyserial -> PL USB-UART -> FPGA UART protocol
```

No RTL, Vivado, XDC, or UART protocol behavior changes are required.

### Host CLI Block Diagram

```text
+----------------------------- PC host -----------------------------+
|                                                                    |
|  +-------------------+      +-----------------------------------+  |
|  | uart_cmd.py       |----->| uart_host_protocol.py             |  |
|  | argparse commands |      | builders/parser/decoders          |  |
|  +-------------------+      +-----------------------------------+  |
|           |                                ^                       |
|           v                                |                       |
|  +-------------------+      validated Response + decoded payloads |
|  | serial transport  |---------------------------------------------+
|  +-------------------+                                             |
+-----------|--------------------------------------------------------+
            |
            | 115200-8-N-1
            v
+-----------|---------------- FPGA PL -------------------------------+
|           v                                                        |
|     uart_rx -> frame_parser -> cmd_dispatcher -> resp_encoder      |
|           ^                                      |                 |
|           +--------------- uart_tx <-------------+                 |
+--------------------------------------------------------------------+
```

### Command Timing Diagram

```text
User shell                 uart_cmd.py                 FPGA PL
    |                          |                          |
    | read-row --row 12        |                          |
    |------------------------->|                          |
    |                          | build 55 LEN OP ARG CHK |
    |                          | open/drain serial        |
    |                          |------------------------->|
    |                          |                          | parse frame
    |                          |                          | execute command
    |                          |<-------------------------|
    |                          | read AA LEN ST OP DATA CHK
    |                          | validate response frame  |
    |                          | decode payload           |
    |<-------------------------|                          |
    | data=00 11 ... exit 0    |                          |
```

## Goals / Non-Goals

**Goals:**

- Provide a direct command-line sender for every currently documented UART command.
- Reuse the current protocol helper instead of duplicating frame constants or checksum logic.
- Keep command output useful for both humans and scripts.
- Make failures actionable: argument errors before TX, serial/protocol errors with command context, and NACK statuses with names and payload bytes.
- Preserve `uart_host_test.py` as the higher-level test/self-check entry point.

**Non-Goals:**

- Do not change FPGA RTL, protocol opcodes, frame layouts, checksums, status codes, or UART physical settings.
- Do not make the CLI a GUI, daemon, REPL, or continuous logger.
- Do not add per-cycle eDRAM pin control.
- Do not require connected hardware for parser/help/protocol self-tests.

## Decisions

### Decision: Add a New Direct Command Script

Add `scripts/uart_cmd.py` as the command-focused entry point.

Expected command shape:

```text
python scripts/uart_cmd.py list
python scripts/uart_cmd.py ping --port /dev/ttyUSB0
python scripts/uart_cmd.py reset --port /dev/ttyUSB0
python scripts/uart_cmd.py status --port /dev/ttyUSB0
python scripts/uart_cmd.py write-row --port /dev/ttyUSB0 --row 12 --data "00 11 22 33 44 55 66 77"
python scripts/uart_cmd.py read-group --port /dev/ttyUSB0 --row 12 --group 3
python scripts/uart_cmd.py read-row --port /dev/ttyUSB0 --row 12
python scripts/uart_cmd.py outputs --port /dev/ttyUSB0
python scripts/uart_cmd.py trace --port /dev/ttyUSB0 --index 0
python scripts/uart_cmd.py raw --port /dev/ttyUSB0 --op 0x05
```

Rationale: `uart_host_test.py` already means "run a validation flow". A separate direct sender keeps the UX clean and avoids mixing one-shot commands with pass/fail test sequences.

Alternative considered: add more subcommands to `uart_host_test.py`. That would reuse existing transport code immediately, but the command surface would become confusing because `read-row` is not a test while `full` is.

### Decision: Reuse and Lightly Factor Existing Host Helpers

`uart_cmd.py` should import `uart_host_protocol.py` for:

- opcode/status constants and names;
- request builders for named commands;
- response parsing and checksum validation;
- row/group/data validation;
- output snapshot and trace payload decoding.

If implementation would otherwise duplicate transport code from `uart_host_test.py`, extract the common pieces into a small helper such as `scripts/uart_serial_transport.py`:

- lazy `pyserial` import and install hint;
- serial port listing;
- serial open/drain/close;
- one-request/one-response exchange;
- timeout and malformed-frame diagnostics.

Rationale: protocol logic is already centralized, and the existing test CLI has proven serial exchange behavior. Factoring the transport keeps both CLIs consistent without forcing the new command CLI to import a test module.

Alternative considered: duplicate the serial helpers inside `uart_cmd.py`. That is faster initially but creates two timeout, resynchronization, and pyserial error paths to maintain.

### Decision: Support Human and JSON Output

Default output should be concise and command-specific:

```text
PING ACK payload=A5
STATUS ACK busy=0 last_err=ACK(0x00)
READ_GROUP ACK row=12 group=3 data=5A
READ_ROW ACK row=12 data=00 11 22 33 44 55 66 77
OUTPUTS ACK LOAD_N=1 READ_N=1 EN_WWL_N=1 EN_RWL_N=1 WG=0 RG=0 DIN=0x00 A=0 W=0
```

Add `--json` for scripts. JSON should include at least `ok`, `status`, `status_name`, `op`, `op_name`, `data_hex`, and `raw_rx_hex`; command-specific fields can be added for decoded values. Add `--verbose` to print raw TX/RX frames in the human output path.

Rationale: humans need fast readable answers during bring-up, while automation needs a stable parseable shape.

Alternative considered: only print hex frames. That is universal but pushes protocol decoding back onto the user, which is exactly what this CLI should avoid.

### Decision: Include a Raw Diagnostic Command

The `raw` command should build a valid protocol request from user-provided bytes:

```text
python scripts/uart_cmd.py raw --port /dev/ttyUSB0 --op 0x07 --args 00
python scripts/uart_cmd.py raw --port /dev/ttyUSB0 --op 0x99 --allow-nack
```

Behavior:

- validate `--op` and every `--args` byte as `0..255`;
- send the frame using the normal checksum builder;
- parse and print the response with status/op names where known;
- return non-zero on NACK by default, with an option such as `--allow-nack` for negative protocol tests.

Rationale: bring-up often needs a controlled way to exercise NACKs, future opcodes, or undocumented debug commands without writing another Python script.

Alternative considered: allow users to send a complete raw byte frame. That is useful for checksum-corruption tests but less safe as the primary path. If needed later, a separate `raw-frame` command can be added.

### Decision: Keep Hardware-Free Checks

The implementation should keep these checks runnable without an attached FPGA:

```text
python scripts/uart_host_protocol.py
python -m py_compile scripts/uart_host_protocol.py scripts/uart_host_test.py scripts/uart_cmd.py
python scripts/uart_cmd.py --help
python scripts/uart_cmd.py read-row --row 64 --port dummy
```

The invalid argument command should fail before attempting to open the serial port.

Rationale: CI/local validation can cover the command parser, protocol helpers, and argument guards even when no board is connected.

Alternative considered: rely only on manual hardware checks. That would leave parsing and formatting regressions too easy to miss.

### Modules to Be Revised

```text
scripts/
  uart_cmd.py                 new direct UART command CLI
  uart_host_protocol.py       reuse existing builders/decoders; add helpers only if needed
  uart_host_test.py           optional import from shared serial helper after extraction
  uart_serial_transport.py    optional shared serial transport helper

README.md                    add command CLI section and examples

openspec/changes/add-uart-command-cli/
  specs/uart-command-cli/spec.md
  design.md
  tasks.md
```

## Risks / Trade-offs

- [Risk] Two UART CLIs may confuse users. -> Mitigation: document `uart_cmd.py` as single-command sender and `uart_host_test.py` as validation/self-check runner.
- [Risk] Shared transport extraction could accidentally change existing test behavior. -> Mitigation: keep the helper API small and rerun existing `uart_host_test.py --help` plus mocked serial flows if available.
- [Risk] JSON output can become unstable if it mirrors every print string. -> Mitigation: define a compact field set and treat command-specific decoded fields as additive.
- [Risk] Hardware serial timeouts vary by adapter and host OS. -> Mitigation: retain configurable `--timeout`, `--baud`, `--no-drain`, and verbose raw-frame diagnostics.
- [Risk] `raw` can send unsupported or unsafe future commands. -> Mitigation: it still sends framed UART requests only, validates byte ranges, and defaults to non-zero exit on NACK.

## Migration Plan

1. Add `scripts/uart_cmd.py` and optional shared serial helper.
2. Reuse existing protocol builders and add small formatting helpers only where needed.
3. Update README with direct command examples and the distinction between command and test CLIs.
4. Run hardware-free Python checks.
5. Run a mocked serial exchange for named commands and `raw`.
6. When hardware is available, run `ping`, `status`, `outputs`, and one safe read/write command against the programmed board.

Rollback is simple because no protocol or RTL behavior changes: remove the new CLI/helper and README section, or keep the helper private to `uart_host_test.py` if extraction proves unnecessary.

## Open Questions

- Should the script name be `uart_cmd.py` or `uart_cli.py`? The design uses `uart_cmd.py` because it reads naturally as "send this UART command".
- Should `raw` eventually support a complete user-specified frame for checksum-error testing? That is useful for negative testing but not required for direct command sending.
