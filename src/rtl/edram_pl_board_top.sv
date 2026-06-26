`default_nettype none

import edram_pkg::*;

module edram_pl_board_top #(
  parameter int unsigned INPUT_CLK_HZ       = 200_000_000,
  parameter int unsigned CLK_HZ             = 100_000_000,
  parameter real         CLKFBOUT_MULT_F    = 5.000,
  parameter int unsigned DIVCLK_DIVIDE      = 1,
  parameter real         CLKOUT0_DIVIDE_F   = 10.000,
  parameter int unsigned FREQ_TOLERANCE_HZ  = 1,
  parameter bit          CLK_SIM_BYPASS     = 1'b0,
  parameter int unsigned LOCK_DELAY_CYCLES  = 4,
  parameter int unsigned RESET_SYNC_STAGES  = 2,
  parameter int unsigned UART_BAUD = 115200,
  parameter int unsigned T_LOAD_SETUP_CYCLES   = EDRAM_T_LOAD_SETUP_DEFAULT,
  parameter int unsigned T_LOAD_PULSE_CYCLES   = EDRAM_T_LOAD_PULSE_DEFAULT,
  parameter int unsigned T_LOAD_RECOVER_CYCLES = EDRAM_T_LOAD_RECOVER_DEFAULT,
  parameter int unsigned T_WWL_SETUP_CYCLES    = EDRAM_T_WWL_SETUP_DEFAULT,
  parameter int unsigned T_WWL_PULSE_CYCLES    = EDRAM_T_WWL_PULSE_DEFAULT,
  parameter int unsigned T_WWL_RECOVER_CYCLES  = EDRAM_T_WWL_RECOVER_DEFAULT,
  parameter int unsigned T_READ_SETUP_CYCLES   = EDRAM_T_READ_SETUP_DEFAULT,
  parameter int unsigned T_RWL_PULSE_CYCLES    = EDRAM_T_RWL_PULSE_DEFAULT,
  parameter int unsigned T_READ_SAMPLE_CYCLES  = EDRAM_T_READ_SAMPLE_DEFAULT,
  parameter int unsigned T_READ_RECOVER_CYCLES = EDRAM_T_READ_RECOVER_DEFAULT,
  parameter int unsigned CTRL_TIMEOUT_CYCLES   = EDRAM_CTRL_TIMEOUT_DEFAULT,
  parameter int unsigned P_SYNC_STAGES         = 2
) (
  input  logic       pl_clk0_p_i,
  input  logic       pl_clk0_n_i,
  input  logic       rst_ni,

  input  logic       uart_rx_i,
  output logic       uart_tx_o,

  output logic       edram_load_n_o,
  output logic       edram_read_n_o,
  output logic       edram_en_wwl_n_o,
  output logic       edram_en_rwl_n_o,
  output logic [2:0] edram_wg_o,
  output logic [2:0] edram_rg_o,
  output logic [7:0] edram_din_o,
  output logic [5:0] edram_a_o,
  output logic [5:0] edram_w_o,
  input  logic [7:0] edram_p_i
);
  localparam int unsigned RESET_SYNC_WIDTH =
      (RESET_SYNC_STAGES < 1) ? 1 : RESET_SYNC_STAGES;

  logic core_clk;
  logic clk_locked;
  logic core_reset_async_n;
  logic core_rst_ni;
  logic [RESET_SYNC_WIDTH-1:0] reset_sync_q;

  pl_clk_diff_to_single #(
    .INPUT_CLK_HZ(INPUT_CLK_HZ),
    .OUTPUT_CLK_HZ(CLK_HZ),
    .CLKFBOUT_MULT_F(CLKFBOUT_MULT_F),
    .DIVCLK_DIVIDE(DIVCLK_DIVIDE),
    .CLKOUT0_DIVIDE_F(CLKOUT0_DIVIDE_F),
    .FREQ_TOLERANCE_HZ(FREQ_TOLERANCE_HZ),
    .SIM_BYPASS(CLK_SIM_BYPASS),
    .LOCK_DELAY_CYCLES(LOCK_DELAY_CYCLES)
  ) u_pl_clk_diff_to_single (
    .clk_p_i(pl_clk0_p_i),
    .clk_n_i(pl_clk0_n_i),
    .rst_ni(rst_ni),
    .clk_o(core_clk),
    .locked_o(clk_locked)
  );

  assign core_reset_async_n = rst_ni & clk_locked;
  assign core_rst_ni = reset_sync_q[RESET_SYNC_WIDTH-1];

  generate
    if (RESET_SYNC_WIDTH == 1) begin : gen_single_stage_reset_sync
      always_ff @(posedge core_clk or negedge core_reset_async_n) begin
        if (!core_reset_async_n) begin
          reset_sync_q <= '0;
        end else begin
          reset_sync_q <= 1'b1;
        end
      end
    end else begin : gen_multi_stage_reset_sync
      always_ff @(posedge core_clk or negedge core_reset_async_n) begin
        if (!core_reset_async_n) begin
          reset_sync_q <= '0;
        end else begin
          reset_sync_q <= {reset_sync_q[RESET_SYNC_WIDTH-2:0], 1'b1};
        end
      end
    end
  endgenerate

  edram_pl_top #(
    .CLK_HZ(CLK_HZ),
    .UART_BAUD(UART_BAUD),
    .T_LOAD_SETUP_CYCLES(T_LOAD_SETUP_CYCLES),
    .T_LOAD_PULSE_CYCLES(T_LOAD_PULSE_CYCLES),
    .T_LOAD_RECOVER_CYCLES(T_LOAD_RECOVER_CYCLES),
    .T_WWL_SETUP_CYCLES(T_WWL_SETUP_CYCLES),
    .T_WWL_PULSE_CYCLES(T_WWL_PULSE_CYCLES),
    .T_WWL_RECOVER_CYCLES(T_WWL_RECOVER_CYCLES),
    .T_READ_SETUP_CYCLES(T_READ_SETUP_CYCLES),
    .T_RWL_PULSE_CYCLES(T_RWL_PULSE_CYCLES),
    .T_READ_SAMPLE_CYCLES(T_READ_SAMPLE_CYCLES),
    .T_READ_RECOVER_CYCLES(T_READ_RECOVER_CYCLES),
    .CTRL_TIMEOUT_CYCLES(CTRL_TIMEOUT_CYCLES),
    .P_SYNC_STAGES(P_SYNC_STAGES)
  ) u_edram_pl_top (
    .clk_i(core_clk),
    .rst_ni(core_rst_ni),
    .uart_rx_i(uart_rx_i),
    .uart_tx_o(uart_tx_o),
    .edram_load_n_o(edram_load_n_o),
    .edram_read_n_o(edram_read_n_o),
    .edram_en_wwl_n_o(edram_en_wwl_n_o),
    .edram_en_rwl_n_o(edram_en_rwl_n_o),
    .edram_wg_o(edram_wg_o),
    .edram_rg_o(edram_rg_o),
    .edram_din_o(edram_din_o),
    .edram_a_o(edram_a_o),
    .edram_w_o(edram_w_o),
    .edram_p_i(edram_p_i)
  );
endmodule

`default_nettype wire
