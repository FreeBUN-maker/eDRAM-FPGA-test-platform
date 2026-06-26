`default_nettype none

module uart_tx #(
  parameter int unsigned CLK_HZ    = 100_000_000,
  parameter int unsigned UART_BAUD = 115200
) (
  input  logic       clk_i,
  input  logic       rst_ni,
  input  logic [7:0] byte_i,
  input  logic       byte_valid_i,
  output logic       byte_ready_o,
  output logic       tx_o,
  output logic       busy_o
);
  typedef enum logic [1:0] {
    TX_IDLE,
    TX_START,
    TX_DATA,
    TX_STOP
  } tx_state_e;

  tx_state_e state_q;
  logic [7:0] shift_q;
  logic [2:0] bit_idx_q;
  logic baud_tick;
  logic accept;

  assign byte_ready_o = (state_q == TX_IDLE);
  assign busy_o       = (state_q != TX_IDLE);
  assign accept       = byte_valid_i && byte_ready_o;

  uart_baud_gen #(
    .CLK_HZ(CLK_HZ),
    .UART_BAUD(UART_BAUD)
  ) u_baud_gen (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .enable_i((state_q != TX_IDLE) || accept),
    .restart_i(accept),
    .tick_o(baud_tick)
  );

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q   <= TX_IDLE;
      shift_q   <= '0;
      bit_idx_q <= '0;
      tx_o      <= 1'b1;
    end else begin
      unique case (state_q)
        TX_IDLE: begin
          tx_o <= 1'b1;
          if (accept) begin
            shift_q   <= byte_i;
            bit_idx_q <= 3'd0;
            tx_o      <= 1'b0;
            state_q   <= TX_START;
          end
        end

        TX_START: begin
          tx_o <= 1'b0;
          if (baud_tick) begin
            tx_o    <= shift_q[0];
            state_q <= TX_DATA;
          end
        end

        TX_DATA: begin
          tx_o <= shift_q[bit_idx_q];
          if (baud_tick) begin
            if (bit_idx_q == 3'd7) begin
              tx_o    <= 1'b1;
              state_q <= TX_STOP;
            end else begin
              bit_idx_q <= bit_idx_q + 1'b1;
              tx_o      <= shift_q[bit_idx_q + 3'd1];
            end
          end
        end

        TX_STOP: begin
          tx_o <= 1'b1;
          if (baud_tick) begin
            state_q <= TX_IDLE;
          end
        end

        default: state_q <= TX_IDLE;
      endcase
    end
  end
endmodule

`default_nettype wire
