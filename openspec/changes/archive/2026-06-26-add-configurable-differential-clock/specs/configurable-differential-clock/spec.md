## ADDED Requirements

### Requirement: Differential board clock input
The board-level clocking design SHALL accept the AXU5EVB-E PL 200 MHz differential clock as a positive and negative top-level input pair.

#### Scenario: Differential clock ports are exposed
- **WHEN** the board-level top module interface is inspected
- **THEN** it SHALL expose `pl_clk0_p_i` and `pl_clk0_n_i` as input ports
- **AND** it SHALL NOT expose the board clock as a single-ended physical `clk_i` port

#### Scenario: Differential input is converted to core clock
- **WHEN** the board-level top is elaborated for synthesis
- **THEN** the differential input pair SHALL feed a differential input buffer before driving any single-ended clocking logic
- **AND** the resulting generated clock SHALL be distributed to core RTL through a global clock buffer

### Requirement: Parameterized output frequency
The clock conversion module SHALL allow the generated single-ended clock frequency to be controlled by build-time parameters.

#### Scenario: Frequency is derived from MMCM parameters
- **WHEN** the clock module parameters are inspected
- **THEN** they SHALL include an input clock frequency, a feedback multiply value, an input divide value, an output divide value, and a declared output clock frequency
- **AND** the declared output clock frequency SHALL correspond to the MMCM formula `INPUT_CLK_HZ * CLKFBOUT_MULT_F / DIVCLK_DIVIDE / CLKOUT0_DIVIDE_F`

#### Scenario: Core CLK_HZ follows generated clock
- **WHEN** the board wrapper instantiates `edram_pl_top`
- **THEN** it SHALL pass the generated output clock frequency value to `edram_pl_top.CLK_HZ`
- **AND** UART baud timing SHALL be based on the generated single-ended clock frequency rather than the raw 200 MHz differential source when the two differ

### Requirement: Clock lock and reset release
The board-level integration SHALL keep the existing RTL core in reset until the generated clock is locked and reset deassertion is synchronized to that clock domain.

#### Scenario: Reset remains asserted before lock
- **WHEN** external reset is deasserted but the clock generator has not asserted lock
- **THEN** the reset driven into `edram_pl_top.rst_ni` SHALL remain asserted low

#### Scenario: Reset release is synchronized
- **WHEN** external reset is deasserted and the clock generator lock signal is high
- **THEN** the reset driven into `edram_pl_top.rst_ni` SHALL deassert only after synchronization on the generated single-ended clock

### Requirement: Core RTL remains single-clock reusable
The existing `edram_pl_top` core integration module SHALL remain usable with a direct single-ended `clk_i` in simulation and non-board integrations.

#### Scenario: Core top interface is preserved
- **WHEN** `edram_pl_top.sv` is inspected after this change
- **THEN** it SHALL still expose a single-ended `clk_i` input
- **AND** it SHALL NOT directly instantiate Xilinx differential clocking primitives

#### Scenario: Board wrapper adapts physical clock to core clock
- **WHEN** the board-level top instantiates `edram_pl_top`
- **THEN** it SHALL connect the clock conversion module output to `edram_pl_top.clk_i`
- **AND** it SHALL connect the synchronized reset output to `edram_pl_top.rst_ni`

### Requirement: Vivado clock configuration matches board-level ports
The Vivado configuration SHALL describe the differential board clock ports and board pins used by the board-level top.

#### Scenario: Board top and source list include clock wrapper
- **WHEN** `src/vivado/config.json` is inspected
- **THEN** its project top SHALL identify the board-level top module
- **AND** its source list SHALL include the clock conversion module and board-level wrapper source files

#### Scenario: Differential clock pins are resolved
- **WHEN** the clock configuration is inspected
- **THEN** it SHALL identify `pl_clk0_p_i` and `pl_clk0_n_i` as the physical clock ports
- **AND** it SHALL record the AXU5EVB-E package pins `AE5` and `AF5` for the positive and negative clock inputs
- **AND** it SHALL NOT leave the previous single-ended `clk_i` clock mapping as an unresolved required pin

### Requirement: Simulation path avoids vendor primitive dependency
The clock conversion module SHALL provide a simulation path that can be elaborated by the existing Verilator/cocotb flow without Xilinx simulation libraries.

#### Scenario: Simulation bypass drives a test clock
- **WHEN** the clock module is instantiated with simulation bypass enabled
- **THEN** `clk_o` SHALL be driven from a simple simulation-visible clock source
- **AND** `locked_o` SHALL assert in a deterministic way after reset deassertion

#### Scenario: Existing core tests remain valid
- **WHEN** the existing cocotb tests instantiate `edram_pl_top` directly
- **THEN** they SHALL still be able to drive `clk_i` directly without instantiating the board-level clock wrapper
