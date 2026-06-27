`default_nettype none

module uart_rx #(
  parameter int unsigned CLK_HZ    = 100_000_000,
  parameter int unsigned UART_BAUD = 115200
) (
  input  wire logic       clk_i,
  input  wire logic       rst_ni,
  input  wire logic       rx_i,
  output logic [7:0] byte_o,
  output logic       byte_valid_o,
  output logic       framing_error_o
);
  localparam int unsigned CLKS_PER_BIT_RAW =
      (UART_BAUD == 0) ? 1 : ((CLK_HZ + (UART_BAUD / 2)) / UART_BAUD);
  localparam int unsigned CLKS_PER_BIT =
      (CLKS_PER_BIT_RAW < 1) ? 1 : CLKS_PER_BIT_RAW;
  localparam int unsigned HALF_BIT =
      (CLKS_PER_BIT < 2) ? 1 : (CLKS_PER_BIT / 2);
  localparam int unsigned COUNTER_WIDTH =
      (CLKS_PER_BIT <= 1) ? 1 : $clog2(CLKS_PER_BIT + 1);
  localparam int unsigned HALF_BIT_COUNT_INT =
      (HALF_BIT <= 1) ? 0 : (HALF_BIT - 1);
  localparam logic [COUNTER_WIDTH-1:0] HALF_BIT_COUNT =
      COUNTER_WIDTH'(HALF_BIT_COUNT_INT);
  localparam logic [COUNTER_WIDTH-1:0] BIT_COUNT_MAX  =
      COUNTER_WIDTH'(CLKS_PER_BIT - 1);

  typedef enum logic [1:0] {
    RX_IDLE,
    RX_START,
    RX_DATA,
    RX_STOP
  } rx_state_e;

  rx_state_e state_q;
  logic [COUNTER_WIDTH-1:0] count_q;
  logic [2:0] bit_idx_q;
  logic [7:0] shift_q;
  logic rx_meta_q;
  logic rx_sync_q;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      rx_meta_q <= 1'b1;
      rx_sync_q <= 1'b1;
    end else begin
      rx_meta_q <= rx_i;
      rx_sync_q <= rx_meta_q;
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q         <= RX_IDLE;
      count_q         <= '0;
      bit_idx_q       <= '0;
      shift_q         <= '0;
      byte_o          <= '0;
      byte_valid_o    <= 1'b0;
      framing_error_o <= 1'b0;
    end else begin
      byte_valid_o    <= 1'b0;
      framing_error_o <= 1'b0;

      unique case (state_q)
        RX_IDLE: begin
          count_q   <= '0;
          bit_idx_q <= '0;
          if (!rx_sync_q) begin
            state_q <= RX_START;
            count_q <= HALF_BIT_COUNT;
          end
        end

        RX_START: begin
          if (count_q == '0) begin
            if (!rx_sync_q) begin
              state_q   <= RX_DATA;
              count_q   <= BIT_COUNT_MAX;
              bit_idx_q <= 3'd0;
            end else begin
              state_q <= RX_IDLE;
            end
          end else begin
            count_q <= count_q - 1'b1;
          end
        end

        RX_DATA: begin
          if (count_q == '0) begin
            shift_q[bit_idx_q] <= rx_sync_q;
            count_q            <= BIT_COUNT_MAX;
            if (bit_idx_q == 3'd7) begin
              state_q <= RX_STOP;
            end else begin
              bit_idx_q <= bit_idx_q + 1'b1;
            end
          end else begin
            count_q <= count_q - 1'b1;
          end
        end

        RX_STOP: begin
          if (count_q == '0) begin
            state_q <= RX_IDLE;
            if (rx_sync_q) begin
              byte_o       <= shift_q;
              byte_valid_o <= 1'b1;
            end else begin
              framing_error_o <= 1'b1;
            end
          end else begin
            count_q <= count_q - 1'b1;
          end
        end

        default: state_q <= RX_IDLE;
      endcase
    end
  end
endmodule

`default_nettype wire
