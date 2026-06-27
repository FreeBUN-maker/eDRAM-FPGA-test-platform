## Why

After moving the project into a Windows Vivado workspace, the project-mode Tcl flow can add sources and constraints, but the default full flow stops during the xsim compile/analyze step. The Tcl console shows Vivado 2019.1 VRFC errors such as `net type must be explicitly specified for 'clk_i' when default_nettype is none`, which makes the current RTL declaration style incompatible with the strict nettype setting in Vivado simulation.

## What Changes

- Make RTL module input ports explicit Vivado-compatible net declarations while preserving ``default_nettype none``.
- Cover package enum input ports as well as `logic` input ports so xsim does not stop on later modules after `cmd_dispatcher`.
- Keep the project-mode Tcl source handling robust for Windows paths and multi-file source lists.
- Add validation focused on the Vivado failure mode reported in the Tcl console.

## Capabilities

### New Capabilities
- `vivado-xsim-compile-compatibility`: Ensures the board-level RTL sources and Vivado Tcl source helper can be compiled by Vivado xsim/VRFC under strict nettype settings.

### Modified Capabilities
- None.

## Impact

- Affected RTL: `src/rtl/*.sv` module input port declarations.
- Affected Vivado helper: `src/vivado/sources.tcl` source-object lookup should remain one-file-at-a-time and path-safe.
- Affected validation: static checks can confirm explicit input net declarations locally; full xsim validation requires Vivado.

## Non-goals

- Do not relax or remove ``default_nettype none``.
- Do not change UART protocol behavior, eDRAM controller timing, pin constraints, or top-level board interfaces.
- Do not add a workaround that skips simulation before synthesis in the default flow.
