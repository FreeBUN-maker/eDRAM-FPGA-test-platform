`default_nettype none

package edram_pkg;
  localparam logic [7:0] UART_SOF_REQ  = 8'h55;
  localparam logic [7:0] UART_SOF_RESP = 8'haa;

  localparam int unsigned UART_REQ_MAX_ARGS  = 9;
  localparam int unsigned UART_REQ_MAX_LEN   = 1 + UART_REQ_MAX_ARGS;
  localparam int unsigned UART_RESP_MAX_DATA = 8;
  localparam int unsigned UART_RESP_MAX_LEN  = 2 + UART_RESP_MAX_DATA;

  localparam logic [7:0] OP_PING       = 8'h00;
  localparam logic [7:0] OP_WRITE_ROW  = 8'h01;
  localparam logic [7:0] OP_READ_GROUP = 8'h02;
  localparam logic [7:0] OP_READ_ROW   = 8'h03;
  localparam logic [7:0] OP_RESET      = 8'h04;
  localparam logic [7:0] OP_STATUS     = 8'h05;
  localparam logic [7:0] OP_READ_OUTPUTS      = 8'h06;
  localparam logic [7:0] OP_READ_OUTPUT_TRACE = 8'h07;

  localparam logic [7:0] STAT_ACK          = 8'h00;
  localparam logic [7:0] STAT_NACK_BAD_LEN = 8'h01;
  localparam logic [7:0] STAT_NACK_BAD_CHK = 8'h02;
  localparam logic [7:0] STAT_NACK_BAD_OP  = 8'h03;
  localparam logic [7:0] STAT_NACK_BAD_ARG = 8'h04;
  localparam logic [7:0] STAT_NACK_BUSY    = 8'h05;
  localparam logic [7:0] STAT_NACK_TIMEOUT = 8'h06;

  localparam logic [7:0] PING_RESP_DATA = 8'ha5;

  localparam int unsigned EDRAM_ROW_COUNT   = 64;
  localparam int unsigned EDRAM_GROUP_COUNT = 8;
  localparam int unsigned EDRAM_ROW_BYTES   = 8;
  localparam int unsigned EDRAM_OUTPUT_SNAPSHOT_BYTES = 5;
  localparam int unsigned EDRAM_OUTPUT_TRACE_RESP_BYTES =
      2 + EDRAM_OUTPUT_SNAPSHOT_BYTES;
  localparam int unsigned EDRAM_OUTPUT_TRACE_DEPTH_DEFAULT = 16;

  typedef enum logic [1:0] {
    EDRAM_REQ_NONE       = 2'd0,
    EDRAM_REQ_WRITE_ROW  = 2'd1,
    EDRAM_REQ_READ_GROUP = 2'd2
  } edram_req_e;

  localparam int unsigned EDRAM_T_LOAD_SETUP_DEFAULT   = 2;
  localparam int unsigned EDRAM_T_LOAD_PULSE_DEFAULT   = 2;
  localparam int unsigned EDRAM_T_LOAD_RECOVER_DEFAULT = 2;
  localparam int unsigned EDRAM_T_WWL_SETUP_DEFAULT    = 2;
  localparam int unsigned EDRAM_T_WWL_PULSE_DEFAULT    = 2;
  localparam int unsigned EDRAM_T_WWL_RECOVER_DEFAULT  = 2;
  localparam int unsigned EDRAM_T_READ_SETUP_DEFAULT   = 2;
  localparam int unsigned EDRAM_T_RWL_PULSE_DEFAULT    = 2;
  localparam int unsigned EDRAM_T_READ_SAMPLE_DEFAULT  = 2;
  localparam int unsigned EDRAM_T_READ_RECOVER_DEFAULT = 2;
  localparam int unsigned EDRAM_CTRL_TIMEOUT_DEFAULT   = 100000;

  function automatic logic [7:0] uart_expected_len(input logic [7:0] op);
    unique case (op)
      OP_PING:       uart_expected_len = 8'd1;
      OP_WRITE_ROW:  uart_expected_len = 8'd10;
      OP_READ_GROUP: uart_expected_len = 8'd3;
      OP_READ_ROW:   uart_expected_len = 8'd2;
      OP_RESET:      uart_expected_len = 8'd1;
      OP_STATUS:     uart_expected_len = 8'd1;
      OP_READ_OUTPUTS:      uart_expected_len = 8'd1;
      OP_READ_OUTPUT_TRACE: uart_expected_len = 8'd2;
      default:       uart_expected_len = 8'd0;
    endcase
  endfunction
endpackage

`default_nettype wire
