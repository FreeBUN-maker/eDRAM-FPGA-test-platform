`default_nettype none

import edram_pkg::*;

module uart_resp_encoder (
  input  wire logic                                      clk_i,
  input  wire logic                                      rst_ni,
  input  wire logic                                      resp_valid_i,
  output logic                                      resp_ready_o,
  input  wire logic [7:0]                                resp_status_i,
  input  wire logic [7:0]                                resp_op_i,
  input  wire logic [3:0]                                resp_data_len_i,
  input  wire logic [UART_RESP_MAX_DATA*8-1:0]           resp_data_i,
  output logic [7:0]                                tx_byte_o,
  output logic                                      tx_valid_o,
  input  wire logic                                      tx_ready_i,
  output logic                                      busy_o
);
  localparam logic [3:0] RESP_MAX_DATA_N = 4'(UART_RESP_MAX_DATA);

  logic sending_q;
  logic [3:0] byte_idx_q;
  logic [3:0] total_bytes_q;
  logic [3:0] data_len_q;
  logic [7:0] status_q;
  logic [7:0] op_q;
  logic [7:0] checksum_q;
  logic [UART_RESP_MAX_DATA*8-1:0] data_q;

  assign resp_ready_o = !sending_q;
  assign busy_o       = sending_q;

  function automatic logic [7:0] calc_checksum(
      input logic [7:0] status,
      input logic [7:0] op,
      input logic [3:0] data_len,
      input logic [UART_RESP_MAX_DATA*8-1:0] data
  );
    logic [7:0] chk;
    chk = 8'd2 + {4'd0, data_len};
    chk = chk ^ status ^ op;
    for (int i = 0; i < UART_RESP_MAX_DATA; i++) begin
      if (i < data_len) begin
        chk = chk ^ data[i*8 +: 8];
      end
    end
    return chk;
  endfunction

  function automatic logic [7:0] frame_byte(
      input logic [3:0] index,
      input logic [3:0] data_len,
      input logic [7:0] status,
      input logic [7:0] op,
      input logic [7:0] checksum,
      input logic [UART_RESP_MAX_DATA*8-1:0] data
  );
    if (index == 4'd0) begin
      frame_byte = UART_SOF_RESP;
    end else if (index == 4'd1) begin
      frame_byte = 8'd2 + {4'd0, data_len};
    end else if (index == 4'd2) begin
      frame_byte = status;
    end else if (index == 4'd3) begin
      frame_byte = op;
    end else if (index == (4'd4 + data_len)) begin
      frame_byte = checksum;
    end else begin
      frame_byte = data[(index - 4'd4) * 8 +: 8];
    end
  endfunction

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      sending_q     <= 1'b0;
      byte_idx_q    <= '0;
      total_bytes_q <= '0;
      data_len_q    <= '0;
      status_q      <= '0;
      op_q          <= '0;
      checksum_q    <= '0;
      data_q        <= '0;
      tx_byte_o     <= '0;
      tx_valid_o    <= 1'b0;
    end else begin
      if (!sending_q) begin
        tx_valid_o <= 1'b0;
        if (resp_valid_i) begin
          data_len_q    <= (resp_data_len_i > RESP_MAX_DATA_N) ?
                           RESP_MAX_DATA_N : resp_data_len_i;
          status_q      <= resp_status_i;
          op_q          <= resp_op_i;
          data_q        <= resp_data_i;
          checksum_q    <= calc_checksum(
                              resp_status_i,
                              resp_op_i,
                              (resp_data_len_i > RESP_MAX_DATA_N) ?
                                  RESP_MAX_DATA_N : resp_data_len_i,
                              resp_data_i
                            );
          total_bytes_q <= 4'd5 + ((resp_data_len_i > RESP_MAX_DATA_N) ?
                           RESP_MAX_DATA_N : resp_data_len_i);
          byte_idx_q    <= 4'd1;
          tx_byte_o     <= UART_SOF_RESP;
          tx_valid_o    <= 1'b1;
          sending_q     <= 1'b1;
        end
      end else if (tx_valid_o && tx_ready_i) begin
        if (byte_idx_q == total_bytes_q) begin
          tx_valid_o <= 1'b0;
          sending_q  <= 1'b0;
        end else begin
          tx_byte_o  <= frame_byte(
                          byte_idx_q,
                          data_len_q,
                          status_q,
                          op_q,
                          checksum_q,
                          data_q
                        );
          tx_valid_o <= 1'b1;
          byte_idx_q <= byte_idx_q + 1'b1;
        end
      end
    end
  end
endmodule

`default_nettype wire
