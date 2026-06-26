`timescale 1ns/1ps
`default_nettype none

module edram_pl_board_top_vivado_tb;
  localparam real CLK_HALF_PERIOD_NS = 2.5;

  logic       pl_clk0_p_i = 1'b0;
  logic       pl_clk0_n_i = 1'b1;
  logic       rst_ni      = 1'b0;
  logic       uart_rx_i   = 1'b1;
  logic       uart_tx_o;
  logic       edram_load_n_o;
  logic       edram_read_n_o;
  logic       edram_en_wwl_n_o;
  logic       edram_en_rwl_n_o;
  logic [2:0] edram_wg_o;
  logic [2:0] edram_rg_o;
  logic [7:0] edram_din_o;
  logic [5:0] edram_a_o;
  logic [5:0] edram_w_o;
  logic [7:0] edram_p_i  = 8'h00;

  always #(CLK_HALF_PERIOD_NS) begin
    pl_clk0_p_i = ~pl_clk0_p_i;
    pl_clk0_n_i = ~pl_clk0_n_i;
  end

  edram_pl_board_top #(
    .CLK_SIM_BYPASS(1'b1),
    .LOCK_DELAY_CYCLES(2),
    .RESET_SYNC_STAGES(2)
  ) dut (
    .pl_clk0_p_i(pl_clk0_p_i),
    .pl_clk0_n_i(pl_clk0_n_i),
    .rst_ni(rst_ni),
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

  initial begin
    repeat (8) @(posedge pl_clk0_p_i);
    rst_ni = 1'b1;

    repeat (64) @(posedge pl_clk0_p_i);

    if (uart_tx_o !== 1'b1) begin
      $fatal(1, "UART TX is not idle high after reset");
    end
    if (edram_load_n_o !== 1'b1 ||
        edram_read_n_o !== 1'b1 ||
        edram_en_wwl_n_o !== 1'b1 ||
        edram_en_rwl_n_o !== 1'b1) begin
      $fatal(1, "eDRAM active-low controls are not idle high after reset");
    end

    $display("edram_pl_board_top_vivado_tb completed");
    $finish;
  end
endmodule

`default_nettype wire
