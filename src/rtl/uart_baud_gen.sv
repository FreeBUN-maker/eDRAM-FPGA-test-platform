`default_nettype none

module uart_baud_gen #(
  parameter int unsigned CLK_HZ    = 100_000_000,
  parameter int unsigned UART_BAUD = 115200
) (
  input  logic clk_i,
  input  logic rst_ni,
  input  logic enable_i,
  input  logic restart_i,
  output logic tick_o
);
  localparam int unsigned CLKS_PER_BIT_RAW =
      (UART_BAUD == 0) ? 1 : ((CLK_HZ + (UART_BAUD / 2)) / UART_BAUD);
  localparam int unsigned CLKS_PER_BIT =
      (CLKS_PER_BIT_RAW < 1) ? 1 : CLKS_PER_BIT_RAW;
  localparam int unsigned COUNTER_WIDTH =
      (CLKS_PER_BIT <= 1) ? 1 : $clog2(CLKS_PER_BIT);
  localparam logic [COUNTER_WIDTH-1:0] CLKS_PER_BIT_M1 =
      COUNTER_WIDTH'(CLKS_PER_BIT - 1);

  logic [COUNTER_WIDTH-1:0] count_q;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      count_q <= '0;
      tick_o  <= 1'b0;
    end else begin
      tick_o <= 1'b0;

      if (!enable_i || restart_i) begin
        count_q <= '0;
      end else if (CLKS_PER_BIT == 1) begin
        tick_o <= 1'b1;
      end else if (count_q == CLKS_PER_BIT_M1) begin
        count_q <= '0;
        tick_o  <= 1'b1;
      end else begin
        count_q <= count_q + 1'b1;
      end
    end
  end
endmodule

`default_nettype wire
