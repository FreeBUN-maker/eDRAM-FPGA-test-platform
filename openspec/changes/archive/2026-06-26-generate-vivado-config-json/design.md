## Context

`src/vivado/config.json` 当前为空对象，而 `src/rtl/edram_pl_top.sv` 已经定义了 PL-only 顶层端口。Vivado Tcl 流程需要一个稳定的机器可读配置，才能创建工程、加入 RTL 文件、设置目标器件，并从同一个源生成时钟约束和引脚约束。

输入依据包括：

- `prompt.md` 中指定的目标器件：`xczu5ev-sfvc784-1-i`。
- `src/rtl/edram_pl_top.sv` 中的顶层端口和参数默认值。
- `FPGA-instruction/AXU5EVB-E开发板用户手册.pdf` 中的 AXU5EVB-E PL 端时钟、复位、UART 或扩展接口管脚说明。
- 现有 RTL 文件：`edram_pkg.sv`、UART 模块、dispatcher、eDRAM controller 和 PL top。

### Block diagram

```text
 prompt.md
 board manual PDF
 edram_pl_top.sv
       |
       v
+----------------------+
| src/vivado/config.json|
+----------------------+
       |
       v
+----------------------+       +----------------+
| Vivado Tcl flow      | ----> | project setup  |
| - read config        |       | RTL file list  |
| - validate fields    |       | timing XDC     |
| - emit constraints   |       | pin XDC        |
+----------------------+       +----------------+
```

## Goals / Non-Goals

**Goals:**

- Define and fill a JSON structure that Vivado Tcl can consume deterministically.
- Capture the Vivado part, top module, RTL source list, PL clock definition, reset polarity, UART pins, and all eDRAM-facing pins from `edram_pl_top.sv`.
- Keep bus signals represented in a way that preserves bit ordering for XDC generation.
- Record unresolved or unconfirmed pin mappings explicitly so the flow can stop with a clear error instead of emitting misleading constraints.
- Keep the configuration easy to review in Git.

**Non-Goals:**

- Do not change RTL behavior, UART frame semantics, or eDRAM timing state machines.
- Do not build a PS block design or configure ARM-side software.
- Do not claim board-level electrical validation; the JSON only captures intended Vivado constraints.
- Do not infer package pins by port name when the board manual or user-provided mapping does not identify them.

## Decisions

### Decision: Use a single JSON file as the Vivado flow contract

`src/vivado/config.json` will be the canonical Tcl input for project metadata, sources, clocks, and port constraints.

Proposed top-level shape:

```json
{
  "project": {
    "name": "edram_fpga_test_platform",
    "part": "xczu5ev-sfvc784-1-i",
    "top": "edram_pl_top",
    "default_library": "xil_defaultlib"
  },
  "sources": [
    "src/rtl/edram_pkg.sv",
    "src/rtl/uart_baud_gen.sv"
  ],
  "clocks": [
    {
      "name": "pl_clk",
      "port": "clk_i",
      "frequency_hz": 100000000,
      "period_ns": 10.0,
      "package_pin": null,
      "iostandard": "LVCMOS33"
    }
  ],
  "ports": [],
  "unresolved": []
}
```

Rationale: a single file avoids splitting the part number, file list, and pin map across multiple hand-maintained Tcl variables. JSON also keeps bus entries reviewable and testable.

Alternative considered: write constraints directly as XDC. That is simpler for one board revision, but it does not provide structured validation or enough metadata for project creation.

### Decision: Represent every top-level port explicitly

The config will include entries for:

- Scalar system pins: `clk_i`, `rst_ni`, `uart_rx_i`, `uart_tx_o`.
- Active-low eDRAM controls: `edram_load_n_o`, `edram_read_n_o`, `edram_en_wwl_n_o`, `edram_en_rwl_n_o`.
- eDRAM buses: `edram_wg_o[2:0]`, `edram_rg_o[2:0]`, `edram_din_o[7:0]`, `edram_a_o[5:0]`, `edram_w_o[5:0]`, `edram_p_i[7:0]`.

Each port entry will include direction, width, I/O standard, optional package pin list, and a board/manual reference when available.

Example bus entry:

```json
{
  "name": "edram_din_o",
  "direction": "out",
  "width": 8,
  "iostandard": "LVCMOS33",
  "package_pins": [null, null, null, null, null, null, null, null],
  "xdc_ports": [
    "edram_din_o[0]",
    "edram_din_o[1]",
    "edram_din_o[2]",
    "edram_din_o[3]",
    "edram_din_o[4]",
    "edram_din_o[5]",
    "edram_din_o[6]",
    "edram_din_o[7]"
  ]
}
```

Rationale: explicit port entries make missing constraints visible and let Tcl generate a stable XDC command per bit.

Alternative considered: compact vector syntax such as `"edram_din_o": ["PIN0", ...]`. That is shorter but loses direction, width, and validation metadata.

### Decision: Treat unconfirmed pins as unresolved constraints

When a package pin cannot be confidently mapped from the AXU5EVB-E manual and current design intent, the JSON will keep the pin value as `null` and add a matching record to `unresolved`.

Example:

```json
{
  "port": "edram_p_i[0]",
  "reason": "Package pin not confirmed from AXU5EVB-E manual/user mapping",
  "required_for": "pin_xdc"
}
```

The Vivado Tcl flow should refuse to emit final pin XDC when unresolved required pins remain.

Rationale: a wrong eDRAM pin map can silently invalidate hardware tests or drive the wrong external signal. Failing loudly is safer than filling guessed package pins.

Alternative considered: use placeholder package pin strings such as `"TBD"`. Null plus structured unresolved records are easier for Tcl and JSON validators to distinguish from a real pin name.

### Decision: Keep timing constraints limited to board clock creation

The initial JSON will include a `create_clock`-equivalent definition for `clk_i`, including `frequency_hz` and `period_ns`. eDRAM transaction setup/pulse/sample parameters remain RTL parameters and simulation concerns, not Vivado timing exceptions.

### Timing diagram

```text
config load       validate fields        generate constraints        Vivado project
    |                   |                         |                         |
    v                   v                         v                         v
read JSON ----> part/top/sources ok ----> create_clock clk_i ----> synth/impl input
                     |
                     +----> unresolved pins? ----> stop before final pin XDC
                                             |
                                             +----> no unresolved pins -> PACKAGE_PIN/IOSTANDARD XDC
```

Rationale: Vivado timing constraints should describe FPGA clocking and I/O placement. The eDRAM protocol timing is already parameterized in RTL and verified by simulation tests.

Alternative considered: encode eDRAM setup and pulse cycles in JSON. That would duplicate RTL parameters unless the Tcl flow also overrides synthesis parameters, which is not part of this change.

## Risks / Trade-offs

- PDF pin tables may be hard to extract automatically -> Cross-check any extracted pins against manual screenshots or user-provided mapping before marking them resolved.
- AXU5EVB-E may expose multiple candidate PL connectors for eDRAM wiring -> Keep board connector and manual reference fields in JSON and leave conflicting choices unresolved.
- Default PL clock frequency may differ from the RTL default `100_000_000` -> Store both `frequency_hz` and `period_ns`, and mark the clock pin/frequency unresolved if the manual does not confirm it.
- JSON schema is local to the Tcl flow -> Add validation tasks so malformed or incomplete JSON fails before Vivado runs.

## Migration Plan

1. Extract the current RTL source list and top-level port list from `src/rtl`.
2. Review the AXU5EVB-E manual for target part, PL clock, reset, UART, and chosen expansion connector package pins.
3. Populate `src/vivado/config.json` with confirmed fields and structured unresolved entries for anything still missing.
4. Run JSON validation and, when available, the Vivado Tcl dry-run or constraint generation command.
5. Roll back by restoring the previous empty `src/vivado/config.json` if the downstream Tcl flow cannot consume the new structure.

## Open Questions

- Which AXU5EVB-E connector or header will be physically wired to the external eDRAM board?
- Should UART use a dedicated USB-UART path on the development board or pins on the same expansion connector as eDRAM?
- What package pin and frequency does the project want for `clk_i` if the board provides multiple PL clock sources?
- Should reset use an onboard key/switch, an external connector pin, or a synthesized reset held inactive in early bring-up?

## System Impact

- `src/vivado/config.json` becomes a reviewed source file instead of an empty placeholder.
- Future Vivado Tcl scripts can derive project setup and XDC content from one source.
- RTL and simulation modules remain unchanged.
- Hardware bring-up becomes dependent on explicit pin confirmation rather than implicit Tcl defaults.

## Modules to be revised

- `src/vivado/config.json`
- Future or existing `src/vivado/*.tcl` consumers that read the JSON, if present during implementation
