`default_nettype none

import edram_pkg::*;

module cmd_dispatcher (
  input  wire logic                                      clk_i,
  input  wire logic                                      rst_ni,

  input  wire logic                                      cmd_valid_i,
  input  wire logic [7:0]                                cmd_op_i,
  input  wire logic [7:0]                                cmd_len_i,
  input  wire logic [UART_REQ_MAX_ARGS*8-1:0]            cmd_args_i,

  input  wire logic                                      parse_err_valid_i,
  input  wire logic [7:0]                                parse_err_status_i,
  input  wire logic [7:0]                                parse_err_op_i,

  output logic                                      resp_valid_o,
  input  wire logic                                      resp_ready_i,
  output logic [7:0]                                resp_status_o,
  output logic [7:0]                                resp_op_o,
  output logic [3:0]                                resp_data_len_o,
  output logic [UART_RESP_MAX_DATA*8-1:0]           resp_data_o,

  output logic                                      edram_req_valid_o,
  input  wire logic                                      edram_req_ready_i,
  output edram_req_e                                edram_req_op_o,
  output logic [5:0]                                edram_req_row_o,
  output logic [2:0]                                edram_req_group_o,
  output logic [EDRAM_ROW_BYTES*8-1:0]              edram_req_write_data_o,
  input  wire logic                                      edram_busy_i,
  input  wire logic                                      edram_done_i,
  input  wire logic                                      edram_timeout_i,
  input  wire logic [7:0]                                edram_read_data_i,
  output logic                                      edram_soft_reset_o
);
  typedef enum logic [2:0] {
    DISP_IDLE,
    DISP_ISSUE_WRITE,
    DISP_WAIT_WRITE,
    DISP_ISSUE_READ_GROUP,
    DISP_WAIT_READ_GROUP,
    DISP_ISSUE_READ_ROW,
    DISP_WAIT_READ_ROW,
    DISP_RESPOND
  } dispatcher_state_e;

  dispatcher_state_e state_q;
  logic [7:0] current_op_q;
  logic [5:0] row_q;
  logic [2:0] group_q;
  logic [2:0] read_idx_q;
  logic [EDRAM_ROW_BYTES*8-1:0] write_data_q;
  logic [UART_RESP_MAX_DATA*8-1:0] read_data_q;
  logic [7:0] last_err_q;

  assign edram_req_valid_o = (state_q == DISP_ISSUE_WRITE) ||
                             (state_q == DISP_ISSUE_READ_GROUP) ||
                             (state_q == DISP_ISSUE_READ_ROW);
  assign edram_req_op_o = (state_q == DISP_ISSUE_WRITE) ?
                          EDRAM_REQ_WRITE_ROW : EDRAM_REQ_READ_GROUP;
  assign edram_req_row_o        = row_q;
  assign edram_req_group_o      = (state_q == DISP_ISSUE_READ_ROW) ? read_idx_q : group_q;
  assign edram_req_write_data_o = write_data_q;

  function automatic logic [UART_RESP_MAX_DATA*8-1:0] payload1(
      input logic [7:0] b0
  );
    payload1        = '0;
    payload1[7:0]   = b0;
  endfunction

  function automatic logic [UART_RESP_MAX_DATA*8-1:0] payload2(
      input logic [7:0] b0,
      input logic [7:0] b1
  );
    payload2          = '0;
    payload2[7:0]     = b0;
    payload2[15:8]    = b1;
  endfunction

  function automatic logic [UART_RESP_MAX_DATA*8-1:0] with_byte(
      input logic [UART_RESP_MAX_DATA*8-1:0] data,
      input logic [2:0] index,
      input logic [7:0] value
  );
    with_byte                    = data;
    with_byte[index * 8 +: 8]    = value;
  endfunction

  task automatic queue_response(
      input logic [7:0] status,
      input logic [7:0] op,
      input logic [3:0] data_len,
      input logic [UART_RESP_MAX_DATA*8-1:0] data
  );
    begin
      resp_status_o   <= status;
      resp_op_o       <= op;
      resp_data_len_o <= data_len;
      resp_data_o     <= data;
      resp_valid_o    <= 1'b1;
      state_q         <= DISP_RESPOND;

      if (status != STAT_ACK) begin
        last_err_q <= status;
      end
    end
  endtask

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q                <= DISP_IDLE;
      current_op_q           <= '0;
      row_q                  <= '0;
      group_q                <= '0;
      read_idx_q             <= '0;
      write_data_q           <= '0;
      read_data_q            <= '0;
      last_err_q             <= STAT_ACK;
      resp_valid_o           <= 1'b0;
      resp_status_o          <= STAT_ACK;
      resp_op_o              <= '0;
      resp_data_len_o        <= '0;
      resp_data_o            <= '0;
      edram_soft_reset_o     <= 1'b0;
    end else begin
      edram_soft_reset_o <= 1'b0;

      unique case (state_q)
        DISP_IDLE: begin
          if (parse_err_valid_i) begin
            queue_response(parse_err_status_i, parse_err_op_i, 4'd0, '0);
          end else if (cmd_valid_i) begin
            current_op_q <= cmd_op_i;

            if (uart_expected_len(cmd_op_i) == 8'd0) begin
              queue_response(STAT_NACK_BAD_OP, cmd_op_i, 4'd0, '0);
            end else if (cmd_len_i != uart_expected_len(cmd_op_i)) begin
              queue_response(STAT_NACK_BAD_LEN, cmd_op_i, 4'd0, '0);
            end else begin
              unique case (cmd_op_i)
                OP_PING: begin
                  queue_response(STAT_ACK, OP_PING, 4'd1, payload1(PING_RESP_DATA));
                end

                OP_RESET: begin
                  last_err_q         <= STAT_ACK;
                  edram_soft_reset_o <= 1'b1;
                  queue_response(STAT_ACK, OP_RESET, 4'd0, '0);
                end

                OP_STATUS: begin
                  queue_response(
                    STAT_ACK,
                    OP_STATUS,
                    4'd2,
                    payload2({7'd0, edram_busy_i}, last_err_q)
                  );
                end

                OP_WRITE_ROW: begin
                  if (cmd_args_i[7:0] > 8'd63) begin
                    queue_response(STAT_NACK_BAD_ARG, OP_WRITE_ROW, 4'd0, '0);
                  end else if (edram_busy_i || !edram_req_ready_i) begin
                    queue_response(STAT_NACK_BUSY, OP_WRITE_ROW, 4'd0, '0);
                  end else begin
                    row_q <= cmd_args_i[5:0];
                    for (int i = 0; i < EDRAM_ROW_BYTES; i++) begin
                      write_data_q[i*8 +: 8] <= cmd_args_i[(i + 1) * 8 +: 8];
                    end
                    state_q <= DISP_ISSUE_WRITE;
                  end
                end

                OP_READ_GROUP: begin
                  if (cmd_args_i[7:0] > 8'd63) begin
                    queue_response(STAT_NACK_BAD_ARG, OP_READ_GROUP, 4'd0, '0);
                  end else if (cmd_args_i[15:8] > 8'd7) begin
                    queue_response(STAT_NACK_BAD_ARG, OP_READ_GROUP, 4'd0, '0);
                  end else if (edram_busy_i || !edram_req_ready_i) begin
                    queue_response(STAT_NACK_BUSY, OP_READ_GROUP, 4'd0, '0);
                  end else begin
                    row_q   <= cmd_args_i[5:0];
                    group_q <= cmd_args_i[10:8];
                    state_q <= DISP_ISSUE_READ_GROUP;
                  end
                end

                OP_READ_ROW: begin
                  if (cmd_args_i[7:0] > 8'd63) begin
                    queue_response(STAT_NACK_BAD_ARG, OP_READ_ROW, 4'd0, '0);
                  end else if (edram_busy_i || !edram_req_ready_i) begin
                    queue_response(STAT_NACK_BUSY, OP_READ_ROW, 4'd0, '0);
                  end else begin
                    row_q      <= cmd_args_i[5:0];
                    read_idx_q <= 3'd0;
                    read_data_q <= '0;
                    state_q    <= DISP_ISSUE_READ_ROW;
                  end
                end

                default: begin
                  queue_response(STAT_NACK_BAD_OP, cmd_op_i, 4'd0, '0);
                end
              endcase
            end
          end
        end

        DISP_ISSUE_WRITE: begin
          if (edram_req_ready_i) begin
            state_q <= DISP_WAIT_WRITE;
          end
        end

        DISP_WAIT_WRITE: begin
          if (edram_timeout_i) begin
            queue_response(STAT_NACK_TIMEOUT, current_op_q, 4'd0, '0);
          end else if (edram_done_i) begin
            queue_response(STAT_ACK, current_op_q, 4'd0, '0);
          end
        end

        DISP_ISSUE_READ_GROUP: begin
          if (edram_req_ready_i) begin
            state_q <= DISP_WAIT_READ_GROUP;
          end
        end

        DISP_WAIT_READ_GROUP: begin
          if (edram_timeout_i) begin
            queue_response(STAT_NACK_TIMEOUT, current_op_q, 4'd0, '0);
          end else if (edram_done_i) begin
            queue_response(STAT_ACK, current_op_q, 4'd1, payload1(edram_read_data_i));
          end
        end

        DISP_ISSUE_READ_ROW: begin
          if (edram_req_ready_i) begin
            state_q <= DISP_WAIT_READ_ROW;
          end
        end

        DISP_WAIT_READ_ROW: begin
          if (edram_timeout_i) begin
            queue_response(STAT_NACK_TIMEOUT, current_op_q, 4'd0, '0);
          end else if (edram_done_i) begin
            read_data_q[read_idx_q * 8 +: 8] <= edram_read_data_i;
            if (read_idx_q == 3'd7) begin
              queue_response(
                STAT_ACK,
                current_op_q,
                4'd8,
                with_byte(read_data_q, read_idx_q, edram_read_data_i)
              );
            end else begin
              read_idx_q <= read_idx_q + 1'b1;
              state_q    <= DISP_ISSUE_READ_ROW;
            end
          end
        end

        DISP_RESPOND: begin
          if (resp_valid_o && resp_ready_i) begin
            resp_valid_o <= 1'b0;
            state_q      <= DISP_IDLE;
          end
        end

        default: state_q <= DISP_IDLE;
      endcase
    end
  end
endmodule

`default_nettype wire
