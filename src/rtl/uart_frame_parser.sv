`default_nettype none

import edram_pkg::*;

module uart_frame_parser (
  input  wire logic                                      clk_i,
  input  wire logic                                      rst_ni,
  input  wire logic                                      clear_i,
  input  wire logic [7:0]                                byte_i,
  input  wire logic                                      byte_valid_i,
  input  wire logic                                      framing_error_i,
  output logic                                      cmd_valid_o,
  output logic [7:0]                                cmd_op_o,
  output logic [7:0]                                cmd_len_o,
  output logic [UART_REQ_MAX_ARGS*8-1:0]            cmd_args_o,
  output logic                                      parse_err_valid_o,
  output logic [7:0]                                parse_err_status_o,
  output logic [7:0]                                parse_err_op_o
);
  localparam logic [7:0] REQ_MAX_LEN_BYTE = 8'(UART_REQ_MAX_LEN);

  typedef enum logic [1:0] {
    PARSE_WAIT_SOF,
    PARSE_LEN,
    PARSE_BODY,
    PARSE_CHK
  } parser_state_e;

  parser_state_e state_q;
  logic [7:0] len_q;
  logic [7:0] op_q;
  logic [7:0] checksum_q;
  logic [3:0] body_idx_q;
  logic [UART_REQ_MAX_ARGS*8-1:0] args_q;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q            <= PARSE_WAIT_SOF;
      len_q              <= '0;
      op_q               <= '0;
      checksum_q         <= '0;
      body_idx_q         <= '0;
      args_q             <= '0;
      cmd_valid_o        <= 1'b0;
      cmd_op_o           <= '0;
      cmd_len_o          <= '0;
      cmd_args_o         <= '0;
      parse_err_valid_o  <= 1'b0;
      parse_err_status_o <= '0;
      parse_err_op_o     <= '0;
    end else begin
      cmd_valid_o       <= 1'b0;
      parse_err_valid_o <= 1'b0;

      if (clear_i || framing_error_i) begin
        state_q    <= PARSE_WAIT_SOF;
        len_q      <= '0;
        op_q       <= '0;
        checksum_q <= '0;
        body_idx_q <= '0;
        args_q     <= '0;
      end else if (byte_valid_i) begin
        unique case (state_q)
          PARSE_WAIT_SOF: begin
            if (byte_i == UART_SOF_REQ) begin
              state_q <= PARSE_LEN;
            end
          end

          PARSE_LEN: begin
            if ((byte_i < 8'd1) || (byte_i > REQ_MAX_LEN_BYTE)) begin
              parse_err_valid_o  <= 1'b1;
              parse_err_status_o <= STAT_NACK_BAD_LEN;
              parse_err_op_o     <= 8'h00;
              state_q            <= PARSE_WAIT_SOF;
            end else begin
              len_q      <= byte_i;
              checksum_q <= byte_i;
              body_idx_q <= 4'd0;
              args_q     <= '0;
              state_q    <= PARSE_BODY;
            end
          end

          PARSE_BODY: begin
            checksum_q <= checksum_q ^ byte_i;

            if (body_idx_q == 4'd0) begin
              op_q <= byte_i;
            end else begin
              args_q[(body_idx_q - 4'd1) * 8 +: 8] <= byte_i;
            end

            if (body_idx_q == (len_q[3:0] - 4'd1)) begin
              state_q <= PARSE_CHK;
            end else begin
              body_idx_q <= body_idx_q + 1'b1;
            end
          end

          PARSE_CHK: begin
            if (checksum_q == byte_i) begin
              cmd_valid_o <= 1'b1;
              cmd_op_o    <= op_q;
              cmd_len_o   <= len_q;
              cmd_args_o  <= args_q;
            end else begin
              parse_err_valid_o  <= 1'b1;
              parse_err_status_o <= STAT_NACK_BAD_CHK;
              parse_err_op_o     <= op_q;
            end
            state_q <= PARSE_WAIT_SOF;
          end

          default: state_q <= PARSE_WAIT_SOF;
        endcase
      end
    end
  end
endmodule

`default_nettype wire
