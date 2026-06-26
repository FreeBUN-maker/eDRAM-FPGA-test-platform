`default_nettype none

import edram_pkg::*;

module edram_ctrl_fsm #(
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
  input  logic                         clk_i,
  input  logic                         rst_ni,
  input  logic                         soft_reset_i,

  input  logic                         req_valid_i,
  output logic                         req_ready_o,
  input  edram_req_e                   req_op_i,
  input  logic [5:0]                   req_row_i,
  input  logic [2:0]                   req_group_i,
  input  logic [EDRAM_ROW_BYTES*8-1:0] req_write_data_i,

  output logic                         done_o,
  output logic                         timeout_o,
  output logic [7:0]                   read_data_o,
  output logic                         busy_o,

  output logic                         edram_load_n_o,
  output logic                         edram_read_n_o,
  output logic                         edram_en_wwl_n_o,
  output logic                         edram_en_rwl_n_o,
  output logic [2:0]                   edram_wg_o,
  output logic [2:0]                   edram_rg_o,
  output logic [7:0]                   edram_din_o,
  output logic [5:0]                   edram_a_o,
  output logic [5:0]                   edram_w_o,
  input  logic [7:0]                   edram_p_i
);
  localparam int unsigned LOAD_SETUP_CYCLES =
      (T_LOAD_SETUP_CYCLES < 1) ? 1 : T_LOAD_SETUP_CYCLES;
  localparam int unsigned LOAD_PULSE_CYCLES =
      (T_LOAD_PULSE_CYCLES < 1) ? 1 : T_LOAD_PULSE_CYCLES;
  localparam int unsigned LOAD_RECOVER_CYCLES =
      (T_LOAD_RECOVER_CYCLES < 1) ? 1 : T_LOAD_RECOVER_CYCLES;
  localparam int unsigned WWL_SETUP_CYCLES =
      (T_WWL_SETUP_CYCLES < 1) ? 1 : T_WWL_SETUP_CYCLES;
  localparam int unsigned WWL_PULSE_CYCLES =
      (T_WWL_PULSE_CYCLES < 1) ? 1 : T_WWL_PULSE_CYCLES;
  localparam int unsigned WWL_RECOVER_CYCLES =
      (T_WWL_RECOVER_CYCLES < 1) ? 1 : T_WWL_RECOVER_CYCLES;
  localparam int unsigned READ_SETUP_CYCLES =
      (T_READ_SETUP_CYCLES < 1) ? 1 : T_READ_SETUP_CYCLES;
  localparam int unsigned RWL_PULSE_CYCLES =
      (T_RWL_PULSE_CYCLES < 1) ? 1 : T_RWL_PULSE_CYCLES;
  localparam int unsigned READ_SAMPLE_CYCLES =
      (T_READ_SAMPLE_CYCLES < 1) ? 1 : T_READ_SAMPLE_CYCLES;
  localparam int unsigned READ_RECOVER_CYCLES =
      (T_READ_RECOVER_CYCLES < 1) ? 1 : T_READ_RECOVER_CYCLES;
  localparam int unsigned TIMEOUT_CYCLES =
      (CTRL_TIMEOUT_CYCLES < 1) ? 1 : CTRL_TIMEOUT_CYCLES;
  localparam int unsigned READ_ACTIVE_CYCLES =
      (RWL_PULSE_CYCLES > READ_SAMPLE_CYCLES) ?
      RWL_PULSE_CYCLES : READ_SAMPLE_CYCLES;
  localparam int unsigned P_SYNC_COUNT =
      (P_SYNC_STAGES < 1) ? 1 : P_SYNC_STAGES;

  typedef enum logic [3:0] {
    CTRL_IDLE,
    CTRL_LOAD_SETUP,
    CTRL_LOAD_PULSE,
    CTRL_LOAD_RECOVER,
    CTRL_WWL_SETUP,
    CTRL_WWL_PULSE,
    CTRL_WWL_RECOVER,
    CTRL_READ_SETUP,
    CTRL_RWL_ACTIVE,
    CTRL_READ_RECOVER,
    CTRL_TIMEOUT_RECOVER
  } ctrl_state_e;

  ctrl_state_e state_q;
  logic [31:0] wait_q;
  logic [31:0] timeout_count_q;
  logic [31:0] active_elapsed_q;
  logic sample_done_q;
  logic [5:0] row_q;
  logic [2:0] group_q;
  logic [2:0] write_group_q;
  logic [EDRAM_ROW_BYTES*8-1:0] write_data_q;
  logic [7:0] p_sync_q [0:P_SYNC_COUNT-1];

  assign busy_o      = (state_q != CTRL_IDLE);
  assign req_ready_o = (state_q == CTRL_IDLE);

  function automatic logic [31:0] cycles_m1(input int unsigned cycles);
    cycles_m1 = (cycles <= 1) ? 32'd0 : (cycles - 1);
  endfunction

  function automatic logic timeout_hit(
      input ctrl_state_e state,
      input logic [31:0] count
  );
    timeout_hit = (state != CTRL_IDLE) &&
                  (state != CTRL_TIMEOUT_RECOVER) &&
                  (count >= cycles_m1(TIMEOUT_CYCLES));
  endfunction

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (int i = 0; i < P_SYNC_COUNT; i++) begin
        p_sync_q[i] <= '0;
      end
    end else begin
      p_sync_q[0] <= edram_p_i;
      for (int i = 1; i < P_SYNC_COUNT; i++) begin
        p_sync_q[i] <= p_sync_q[i-1];
      end
    end
  end

  always_comb begin
    edram_load_n_o   = 1'b1;
    edram_read_n_o   = 1'b1;
    edram_en_wwl_n_o = 1'b1;
    edram_en_rwl_n_o = 1'b1;
    edram_wg_o       = 3'd0;
    edram_rg_o       = 3'd0;
    edram_din_o      = 8'd0;
    edram_a_o        = 6'd0;
    edram_w_o        = 6'd0;

    unique case (state_q)
      CTRL_LOAD_SETUP,
      CTRL_LOAD_PULSE,
      CTRL_LOAD_RECOVER: begin
        edram_wg_o     = write_group_q;
        edram_din_o    = write_data_q[write_group_q * 8 +: 8];
        edram_load_n_o = (state_q == CTRL_LOAD_PULSE) ? 1'b0 : 1'b1;
      end

      CTRL_WWL_SETUP,
      CTRL_WWL_PULSE,
      CTRL_WWL_RECOVER: begin
        edram_wg_o       = 3'd7;
        edram_din_o      = write_data_q[7 * 8 +: 8];
        edram_a_o        = row_q;
        edram_en_wwl_n_o = (state_q == CTRL_WWL_PULSE) ? 1'b0 : 1'b1;
      end

      CTRL_READ_SETUP,
      CTRL_RWL_ACTIVE,
      CTRL_READ_RECOVER: begin
        edram_w_o        = row_q;
        edram_rg_o       = group_q;
        edram_read_n_o   = (state_q == CTRL_READ_RECOVER) ? 1'b1 : 1'b0;
        edram_en_rwl_n_o = (state_q == CTRL_RWL_ACTIVE) ? 1'b0 : 1'b1;
      end

      default: begin
      end
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q         <= CTRL_IDLE;
      wait_q          <= '0;
      timeout_count_q <= '0;
      active_elapsed_q <= '0;
      sample_done_q   <= 1'b0;
      row_q           <= '0;
      group_q         <= '0;
      write_group_q   <= '0;
      write_data_q    <= '0;
      done_o          <= 1'b0;
      timeout_o       <= 1'b0;
      read_data_o     <= '0;
    end else begin
      done_o    <= 1'b0;
      timeout_o <= 1'b0;

      if (soft_reset_i) begin
        state_q          <= CTRL_IDLE;
        wait_q           <= '0;
        timeout_count_q  <= '0;
        active_elapsed_q <= '0;
        sample_done_q    <= 1'b0;
      end else if (timeout_hit(state_q, timeout_count_q)) begin
        state_q          <= CTRL_TIMEOUT_RECOVER;
        wait_q           <= cycles_m1(READ_RECOVER_CYCLES);
        timeout_count_q  <= '0;
        active_elapsed_q <= '0;
        sample_done_q    <= 1'b0;
      end else begin
        if ((state_q != CTRL_IDLE) && (state_q != CTRL_TIMEOUT_RECOVER)) begin
          timeout_count_q <= timeout_count_q + 1'b1;
        end else begin
          timeout_count_q <= '0;
        end

        unique case (state_q)
          CTRL_IDLE: begin
            wait_q           <= '0;
            active_elapsed_q <= '0;
            sample_done_q    <= 1'b0;

            if (req_valid_i) begin
              row_q          <= req_row_i;
              group_q        <= req_group_i;
              write_data_q   <= req_write_data_i;
              write_group_q  <= 3'd0;
              timeout_count_q <= '0;

              if (req_op_i == EDRAM_REQ_WRITE_ROW) begin
                state_q <= CTRL_LOAD_SETUP;
                wait_q  <= cycles_m1(LOAD_SETUP_CYCLES);
              end else if (req_op_i == EDRAM_REQ_READ_GROUP) begin
                state_q <= CTRL_READ_SETUP;
                wait_q  <= cycles_m1(READ_SETUP_CYCLES);
              end
            end
          end

          CTRL_LOAD_SETUP: begin
            if (wait_q == 32'd0) begin
              state_q <= CTRL_LOAD_PULSE;
              wait_q  <= cycles_m1(LOAD_PULSE_CYCLES);
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_LOAD_PULSE: begin
            if (wait_q == 32'd0) begin
              state_q <= CTRL_LOAD_RECOVER;
              wait_q  <= cycles_m1(LOAD_RECOVER_CYCLES);
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_LOAD_RECOVER: begin
            if (wait_q == 32'd0) begin
              if (write_group_q == 3'd7) begin
                state_q <= CTRL_WWL_SETUP;
                wait_q  <= cycles_m1(WWL_SETUP_CYCLES);
              end else begin
                write_group_q <= write_group_q + 1'b1;
                state_q       <= CTRL_LOAD_SETUP;
                wait_q        <= cycles_m1(LOAD_SETUP_CYCLES);
              end
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_WWL_SETUP: begin
            if (wait_q == 32'd0) begin
              state_q <= CTRL_WWL_PULSE;
              wait_q  <= cycles_m1(WWL_PULSE_CYCLES);
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_WWL_PULSE: begin
            if (wait_q == 32'd0) begin
              state_q <= CTRL_WWL_RECOVER;
              wait_q  <= cycles_m1(WWL_RECOVER_CYCLES);
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_WWL_RECOVER: begin
            if (wait_q == 32'd0) begin
              done_o  <= 1'b1;
              state_q <= CTRL_IDLE;
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_READ_SETUP: begin
            if (wait_q == 32'd0) begin
              state_q          <= CTRL_RWL_ACTIVE;
              wait_q           <= cycles_m1(READ_ACTIVE_CYCLES);
              active_elapsed_q <= 32'd0;
              sample_done_q    <= 1'b0;
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_RWL_ACTIVE: begin
            if (!sample_done_q &&
                (active_elapsed_q >= cycles_m1(READ_SAMPLE_CYCLES))) begin
              read_data_o   <= p_sync_q[P_SYNC_COUNT-1];
              sample_done_q <= 1'b1;
            end

            if (wait_q == 32'd0) begin
              if (!sample_done_q) begin
                read_data_o <= p_sync_q[P_SYNC_COUNT-1];
              end
              state_q <= CTRL_READ_RECOVER;
              wait_q  <= cycles_m1(READ_RECOVER_CYCLES);
            end else begin
              wait_q           <= wait_q - 1'b1;
              active_elapsed_q <= active_elapsed_q + 1'b1;
            end
          end

          CTRL_READ_RECOVER: begin
            if (wait_q == 32'd0) begin
              done_o  <= 1'b1;
              state_q <= CTRL_IDLE;
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          CTRL_TIMEOUT_RECOVER: begin
            if (wait_q == 32'd0) begin
              timeout_o <= 1'b1;
              state_q   <= CTRL_IDLE;
            end else begin
              wait_q <= wait_q - 1'b1;
            end
          end

          default: state_q <= CTRL_IDLE;
        endcase
      end
    end
  end
endmodule

`default_nettype wire
