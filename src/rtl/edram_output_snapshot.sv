`default_nettype none

import edram_pkg::*;

module edram_output_snapshot #(
  parameter int unsigned TRACE_DEPTH = EDRAM_OUTPUT_TRACE_DEPTH_DEFAULT
) (
  input  wire logic                                clk_i,
  input  wire logic                                rst_ni,
  input  wire logic                                soft_reset_i,
  input  wire logic                                transaction_start_i,

  input  wire logic                                edram_load_n_i,
  input  wire logic                                edram_read_n_i,
  input  wire logic                                edram_en_wwl_n_i,
  input  wire logic                                edram_en_rwl_n_i,
  input  wire logic [2:0]                          edram_wg_i,
  input  wire logic [2:0]                          edram_rg_i,
  input  wire logic [7:0]                          edram_din_i,
  input  wire logic [5:0]                          edram_a_i,
  input  wire logic [5:0]                          edram_w_i,

  output logic [EDRAM_OUTPUT_SNAPSHOT_BYTES*8-1:0] live_snapshot_o,
  input  wire logic [7:0]                          trace_index_i,
  output logic [7:0]                               trace_count_o,
  output logic [EDRAM_OUTPUT_SNAPSHOT_BYTES*8-1:0] trace_snapshot_o,
  output logic                                     trace_index_valid_o
);
  localparam int unsigned SAFE_TRACE_DEPTH = (TRACE_DEPTH < 1) ? 1 : TRACE_DEPTH;
  localparam int unsigned TRACE_INDEX_WIDTH =
      (SAFE_TRACE_DEPTH <= 1) ? 1 : $clog2(SAFE_TRACE_DEPTH);
  localparam logic [7:0] TRACE_DEPTH_BYTE =
      (SAFE_TRACE_DEPTH > 255) ? 8'hff : 8'(SAFE_TRACE_DEPTH);

  logic [EDRAM_OUTPUT_SNAPSHOT_BYTES*8-1:0] trace_q [0:SAFE_TRACE_DEPTH-1];
  logic [7:0] trace_count_q;
  logic [EDRAM_OUTPUT_SNAPSHOT_BYTES*8-1:0] last_snapshot_q;
  logic [EDRAM_OUTPUT_SNAPSHOT_BYTES*8-1:0] packed_snapshot;
  logic active_snapshot;

  assign packed_snapshot[7:0] = {
    4'd0,
    edram_en_rwl_n_i,
    edram_en_wwl_n_i,
    edram_read_n_i,
    edram_load_n_i
  };
  assign packed_snapshot[15:8]  = {2'd0, edram_rg_i, edram_wg_i};
  assign packed_snapshot[23:16] = edram_din_i;
  assign packed_snapshot[31:24] = {2'd0, edram_a_i};
  assign packed_snapshot[39:32] = {2'd0, edram_w_i};

  assign live_snapshot_o = packed_snapshot;
  assign trace_count_o   = trace_count_q;
  assign active_snapshot = !edram_load_n_i || !edram_read_n_i ||
                           !edram_en_wwl_n_i || !edram_en_rwl_n_i;
  assign trace_index_valid_o = (trace_index_i < trace_count_q) &&
                               (trace_index_i < TRACE_DEPTH_BYTE);

  always_comb begin
    trace_snapshot_o = '0;
    if (trace_index_valid_o) begin
      trace_snapshot_o = trace_q[trace_index_i[TRACE_INDEX_WIDTH-1:0]];
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      trace_count_q   <= '0;
      last_snapshot_q <= '0;
      for (int i = 0; i < SAFE_TRACE_DEPTH; i++) begin
        trace_q[i] <= '0;
      end
    end else if (soft_reset_i || transaction_start_i) begin
      trace_count_q   <= '0;
      last_snapshot_q <= '0;
    end else if (active_snapshot &&
                 ((trace_count_q == 8'd0) || (packed_snapshot != last_snapshot_q)) &&
                 (trace_count_q < TRACE_DEPTH_BYTE)) begin
      trace_q[trace_count_q[TRACE_INDEX_WIDTH-1:0]] <= packed_snapshot;
      trace_count_q   <= trace_count_q + 1'b1;
      last_snapshot_q <= packed_snapshot;
    end
  end
endmodule

`default_nettype wire
