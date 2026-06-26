`default_nettype none

import edram_pkg::*;

module edram_pl_top #(
  parameter int unsigned CLK_HZ    = 100_000_000,
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
  input  logic       clk_i,
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
  logic [7:0] rx_byte;
  logic rx_byte_valid;
  logic rx_framing_error;

  logic parser_cmd_valid;
  logic [7:0] parser_cmd_op;
  logic [7:0] parser_cmd_len;
  logic [UART_REQ_MAX_ARGS*8-1:0] parser_cmd_args;
  logic parser_err_valid;
  logic [7:0] parser_err_status;
  logic [7:0] parser_err_op;

  logic disp_resp_valid;
  logic disp_resp_ready;
  logic [7:0] disp_resp_status;
  logic [7:0] disp_resp_op;
  logic [3:0] disp_resp_data_len;
  logic [UART_RESP_MAX_DATA*8-1:0] disp_resp_data;

  logic enc_tx_valid;
  logic enc_tx_ready;
  logic [7:0] enc_tx_byte;

  logic edram_req_valid;
  logic edram_req_ready;
  edram_req_e edram_req_op;
  logic [5:0] edram_req_row;
  logic [2:0] edram_req_group;
  logic [EDRAM_ROW_BYTES*8-1:0] edram_req_write_data;
  logic edram_busy;
  logic edram_done;
  logic edram_timeout;
  logic [7:0] edram_read_data;
  logic edram_soft_reset;
  logic uart_tx_busy;
  logic resp_encoder_busy;

  uart_rx #(
    .CLK_HZ(CLK_HZ),
    .UART_BAUD(UART_BAUD)
  ) u_uart_rx (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .rx_i(uart_rx_i),
    .byte_o(rx_byte),
    .byte_valid_o(rx_byte_valid),
    .framing_error_o(rx_framing_error)
  );

  uart_frame_parser u_uart_frame_parser (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .clear_i(edram_soft_reset),
    .byte_i(rx_byte),
    .byte_valid_i(rx_byte_valid),
    .framing_error_i(rx_framing_error),
    .cmd_valid_o(parser_cmd_valid),
    .cmd_op_o(parser_cmd_op),
    .cmd_len_o(parser_cmd_len),
    .cmd_args_o(parser_cmd_args),
    .parse_err_valid_o(parser_err_valid),
    .parse_err_status_o(parser_err_status),
    .parse_err_op_o(parser_err_op)
  );

  cmd_dispatcher u_cmd_dispatcher (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .cmd_valid_i(parser_cmd_valid),
    .cmd_op_i(parser_cmd_op),
    .cmd_len_i(parser_cmd_len),
    .cmd_args_i(parser_cmd_args),
    .parse_err_valid_i(parser_err_valid),
    .parse_err_status_i(parser_err_status),
    .parse_err_op_i(parser_err_op),
    .resp_valid_o(disp_resp_valid),
    .resp_ready_i(disp_resp_ready),
    .resp_status_o(disp_resp_status),
    .resp_op_o(disp_resp_op),
    .resp_data_len_o(disp_resp_data_len),
    .resp_data_o(disp_resp_data),
    .edram_req_valid_o(edram_req_valid),
    .edram_req_ready_i(edram_req_ready),
    .edram_req_op_o(edram_req_op),
    .edram_req_row_o(edram_req_row),
    .edram_req_group_o(edram_req_group),
    .edram_req_write_data_o(edram_req_write_data),
    .edram_busy_i(edram_busy),
    .edram_done_i(edram_done),
    .edram_timeout_i(edram_timeout),
    .edram_read_data_i(edram_read_data),
    .edram_soft_reset_o(edram_soft_reset)
  );

  edram_ctrl_fsm #(
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
  ) u_edram_ctrl_fsm (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .soft_reset_i(edram_soft_reset),
    .req_valid_i(edram_req_valid),
    .req_ready_o(edram_req_ready),
    .req_op_i(edram_req_op),
    .req_row_i(edram_req_row),
    .req_group_i(edram_req_group),
    .req_write_data_i(edram_req_write_data),
    .done_o(edram_done),
    .timeout_o(edram_timeout),
    .read_data_o(edram_read_data),
    .busy_o(edram_busy),
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

  uart_resp_encoder u_uart_resp_encoder (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .resp_valid_i(disp_resp_valid),
    .resp_ready_o(disp_resp_ready),
    .resp_status_i(disp_resp_status),
    .resp_op_i(disp_resp_op),
    .resp_data_len_i(disp_resp_data_len),
    .resp_data_i(disp_resp_data),
    .tx_byte_o(enc_tx_byte),
    .tx_valid_o(enc_tx_valid),
    .tx_ready_i(enc_tx_ready),
    .busy_o(resp_encoder_busy)
  );

  uart_tx #(
    .CLK_HZ(CLK_HZ),
    .UART_BAUD(UART_BAUD)
  ) u_uart_tx (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .byte_i(enc_tx_byte),
    .byte_valid_i(enc_tx_valid),
    .byte_ready_o(enc_tx_ready),
    .tx_o(uart_tx_o),
    .busy_o(uart_tx_busy)
  );

endmodule

`default_nettype wire
