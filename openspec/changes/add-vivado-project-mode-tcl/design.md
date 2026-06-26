## Context

仓库当前已有板级 Vivado 输入：

- RTL: `src/rtl/edram_pl_board_top.sv` 是板级 top，包含差分 PL 时钟输入、MMCM wrapper、UART 和 eDRAM 外部端口。
- 配置: `src/vivado/config.json` 已记录 project 名称、目标器件 `xczu5ev-sfvc784-1-i`、top `edram_pl_board_top`、默认库、语言和板级端口元数据。
- 源文件 helper: `src/vivado/sources.tcl` 提供 `edram_vivado::add_rtl_sources`，可按既定顺序加入 SystemVerilog RTL。
- 约束: `src/vivado/edram_pl_board.xdc` 已定义 AXU5EVB-E 差分时钟、复位、UART 和 eDRAM 端口管脚约束。
- 仿真: 现有 `sim/tb/*.py` 为 cocotb/Verilator 测试，不是 Vivado xsim 可直接作为 simulation fileset top 的 HDL testbench。

该变更新增一个 project mode Tcl 主入口，使 Vivado GUI 用户可以通过 `Tools -> Run Tcl Script` 执行完整构建流程。

```text
Vivado GUI
  Tools -> Run Tcl Script
        |
        v
src/vivado/run_project_mode.tcl
        |
        +--> src/vivado/config.json        project name / part / top / language
        +--> src/vivado/sources.tcl        ordered RTL add_files helper
        +--> src/vivado/edram_pl_board.xdc board constraints
        +--> sim/tb/*_vivado_tb.sv         xsim smoke simulation top
        |
        v
build/vivado/<project>/
        |
        +--> project creation
        +--> constraints loaded
        +--> xsim smoke simulation
        +--> synth_1
        +--> impl_1
        +--> write_bitstream
```

Overall system impact:

```text
PC host / UART protocol docs
          |
          v
Existing PL-only RTL and board top ----> New Vivado project flow ----> FPGA bitstream
          |                                      ^
          v                                      |
Existing cocotb tests                    Existing XDC + config JSON
```

## Goals / Non-Goals

**Goals:**

- Add `src/vivado/run_project_mode.tcl` as the single GUI-runnable project mode entry point.
- Reuse existing `config.json`, `sources.tcl`, and `edram_pl_board.xdc` rather than duplicating project metadata and RTL source ordering.
- Default to a complete flow: create/open project, add constraints, run Vivado simulation smoke test, synthesize, implement, and generate bitstream.
- Allow optional stage selection for Tcl console or CI-style use without breaking the direct GUI default.
- Add a small Vivado-compatible SystemVerilog smoke testbench so `launch_simulation` has an HDL simulation top.
- Fail early with actionable messages when required inputs, Vivado commands, or generated run results are missing.

**Non-Goals:**

- Do not replace cocotb/Verilator verification or port Python cocotb tests into xsim.
- Do not modify eDRAM control timing, UART protocol behavior, board-level RTL ports, or pin assignments.
- Do not introduce block design, PS configuration, Vitis software, or board automation requiring board files.
- Do not make the script depend on non-standard Tcl packages that may not be available inside Vivado.

## Decisions

### Decision 1: Add a dedicated project mode entry script

The main script will be `src/vivado/run_project_mode.tcl`. It will derive `repo_root` from `[info script]`, so it works when launched from Vivado GUI regardless of the current working directory. It will place generated projects under `build/vivado/<project-name>/` by default.

Alternative considered: extending `sources.tcl` into a full flow script. Rejected because `sources.tcl` is already a focused source-list helper used by both project and non-project flows; keeping the orchestration separate preserves that small API.

Modules revised:

- Add `src/vivado/run_project_mode.tcl`
- Keep using `src/vivado/sources.tcl`
- Keep using `src/vivado/edram_pl_board.xdc`

### Decision 2: Use `config.json` for metadata and `sources.tcl` for source ordering

The script will read known project fields from `config.json`: `project.name`, `project.part`, `project.top`, `project.default_library`, and `project.target_language`. Source file ordering will come from `edram_vivado::add_rtl_sources`, because that Tcl helper is already native to Vivado and mirrors the config source list.

Alternative considered: parse the entire JSON source array in Tcl. Rejected for the first implementation because Vivado Tcl does not guarantee a JSON package, and source ordering already has a maintained Tcl representation.

### Decision 3: Full-flow default with optional stage control

Direct GUI execution should run the full flow without requiring arguments. For advanced use, the script will support optional pre-set global variables or environment variables for project directory, overwrite behavior, and selected stages. The default stage list will be:

```text
create_project -> add_sources -> add_constraints -> simulate -> synthesize -> implement -> bitstream
```

Timing of the build orchestration:

```text
Run Tcl Script
    |
    |-- validate inputs
    |-- create/open project
    |-- add RTL + set top
    |-- add XDC constraints
    |-- run xsim smoke simulation
    |-- launch synth_1 ---- wait_on_run
    |-- launch impl_1  ---- wait_on_run through write_bitstream
    `-- report bitstream path
```

Alternative considered: make the user choose every stage manually in GUI. Rejected because the requested workflow is a direct script execution that completes the build operations.

### Decision 4: Add a Vivado xsim smoke testbench

Add `sim/tb/edram_pl_board_top_vivado_tb.sv` with a short differential clock/reset stimulus. It will instantiate `edram_pl_board_top` with `CLK_SIM_BYPASS=1'b1` to avoid MMCM primitive lock complexity in simulation, drive UART idle high, drive eDRAM readback inputs, and end cleanly after reset and a short idle interval.

Alternative considered: reuse cocotb tests directly from Vivado. Rejected because the existing tests are Python/cocotb and are not a direct HDL simulation top for `launch_simulation`.

### Decision 5: Prefer fail-fast logging over silent GUI continuation

Each phase will validate expected files and run status. Failures will use `return -code error` with a phase-specific message so Vivado GUI surfaces the problem in the Tcl console/messages pane.

Alternative considered: continue past missing simulation files or failed runs. Rejected because a partial GUI run can look successful while producing no trusted bitstream.

## Risks / Trade-offs

- Vivado Tcl JSON parsing is limited -> parse only the stable project metadata fields needed by the script and keep RTL source ordering in `sources.tcl`.
- xsim smoke test is not functional protocol coverage -> document it as a build/simulation sanity check while retaining cocotb tests for behavioral coverage.
- Full-flow default can take a long time in GUI -> expose optional stage selection while keeping the requested one-click default.
- Re-running with an existing build directory may overwrite generated Vivado state -> default to a controlled project directory and provide an overwrite/open-existing policy in the script.
- Local environments may lack Vivado licenses or board-compatible device support -> fail with explicit Vivado run errors and keep static Tcl/source validation available outside Vivado where possible.

## Migration Plan

1. Add the Tcl script and Vivado smoke testbench.
2. Run static checks that required files exist and the Tcl script contains the expected project flow commands.
3. When Vivado is available, execute the script from GUI `Tools -> Run Tcl Script` or Vivado Tcl mode and confirm xsim, synthesis, implementation, and bitstream generation complete.
4. Rollback by removing the new script/testbench and deleting generated `build/vivado/` output; existing RTL, config, and XDC remain unchanged.

## Open Questions

- Whether the Vivado smoke testbench should remain board-top only or later gain a small UART frame stimulus once xsim runtime remains acceptable.
- Whether CI should eventually run a non-GUI Vivado batch invocation of the same script when a licensed runner is available.
