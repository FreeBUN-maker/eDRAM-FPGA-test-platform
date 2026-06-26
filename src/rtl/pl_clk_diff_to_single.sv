`default_nettype none

module pl_clk_diff_to_single #(
  parameter int unsigned INPUT_CLK_HZ       = 200_000_000,
  parameter int unsigned OUTPUT_CLK_HZ      = 100_000_000,
  parameter real         CLKFBOUT_MULT_F    = 5.000,
  parameter int unsigned DIVCLK_DIVIDE      = 1,
  parameter real         CLKOUT0_DIVIDE_F   = 10.000,
  parameter int unsigned FREQ_TOLERANCE_HZ  = 1,
  parameter bit          SIM_BYPASS         = 1'b0,
  parameter int unsigned LOCK_DELAY_CYCLES  = 4
) (
  input  logic clk_p_i,
  input  logic clk_n_i,
  input  logic rst_ni,
  output logic clk_o,
  output logic locked_o
);
  localparam int unsigned LOCK_COUNTER_WIDTH =
      (LOCK_DELAY_CYCLES <= 1) ? 1 : $clog2(LOCK_DELAY_CYCLES + 1);

  function automatic real abs_real(input real value);
    abs_real = (value < 0.0) ? -value : value;
  endfunction

  initial begin : gen_param_check
    real expected_hz;
    real delta_hz;

    if (INPUT_CLK_HZ == 0) begin
      $fatal(1, "INPUT_CLK_HZ must be greater than zero");
    end
    if (OUTPUT_CLK_HZ == 0) begin
      $fatal(1, "OUTPUT_CLK_HZ must be greater than zero");
    end
    if (DIVCLK_DIVIDE == 0) begin
      $fatal(1, "DIVCLK_DIVIDE must be greater than zero");
    end
    if (CLKFBOUT_MULT_F <= 0.0) begin
      $fatal(1, "CLKFBOUT_MULT_F must be greater than zero");
    end
    if (CLKOUT0_DIVIDE_F <= 0.0) begin
      $fatal(1, "CLKOUT0_DIVIDE_F must be greater than zero");
    end
    if (LOCK_DELAY_CYCLES == 0) begin
      $fatal(1, "LOCK_DELAY_CYCLES must be greater than zero");
    end

    expected_hz =
        (real'(INPUT_CLK_HZ) * CLKFBOUT_MULT_F) /
        (real'(DIVCLK_DIVIDE) * CLKOUT0_DIVIDE_F);
    delta_hz = abs_real(expected_hz - real'(OUTPUT_CLK_HZ));

    if (delta_hz > real'(FREQ_TOLERANCE_HZ)) begin
      $fatal(1,
             "OUTPUT_CLK_HZ=%0d does not match MMCM parameters; expected %.3f Hz",
             OUTPUT_CLK_HZ, expected_hz);
    end
  end

`ifdef VERILATOR
  if (SIM_BYPASS == 0) begin : gen_verilator_requires_bypass
    initial begin
      $fatal(1, "Verilator requires SIM_BYPASS=1 for pl_clk_diff_to_single");
    end
  end

  logic [LOCK_COUNTER_WIDTH-1:0] lock_count_q;

  assign clk_o = clk_p_i;

  always_ff @(posedge clk_p_i or negedge rst_ni) begin
    if (!rst_ni) begin
      lock_count_q <= '0;
      locked_o     <= 1'b0;
    end else if (lock_count_q == LOCK_COUNTER_WIDTH'(LOCK_DELAY_CYCLES)) begin
      locked_o <= 1'b1;
    end else begin
      lock_count_q <= lock_count_q + 1'b1;
      locked_o     <= 1'b0;
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  logic unused_clk_n;
  assign unused_clk_n = clk_n_i;
  // verilator lint_on UNUSEDSIGNAL
`else
  generate
    if (SIM_BYPASS != 0) begin : gen_sim_bypass
      logic [LOCK_COUNTER_WIDTH-1:0] lock_count_q;

      assign clk_o = clk_p_i;

      always_ff @(posedge clk_p_i or negedge rst_ni) begin
        if (!rst_ni) begin
          lock_count_q <= '0;
          locked_o     <= 1'b0;
        end else if (lock_count_q == LOCK_COUNTER_WIDTH'(LOCK_DELAY_CYCLES)) begin
          locked_o <= 1'b1;
        end else begin
          lock_count_q <= lock_count_q + 1'b1;
          locked_o     <= 1'b0;
        end
      end

      logic unused_clk_n;
      assign unused_clk_n = clk_n_i;
    end else begin : gen_xilinx_clocking
      localparam real CLKIN1_PERIOD_NS = 1_000_000_000.0 / real'(INPUT_CLK_HZ);

      logic clk_ibuf;
      logic clkfb_mmcm;
      logic clkfb_buf;
      logic clkout0_mmcm;
      logic mmcm_locked;

      IBUFDS #(
        .DIFF_TERM("FALSE"),
        .IBUF_LOW_PWR("TRUE"),
        .IOSTANDARD("LVDS")
      ) u_clk_ibufds (
        .I(clk_p_i),
        .IB(clk_n_i),
        .O(clk_ibuf)
      );

      MMCME4_BASE #(
        .BANDWIDTH("OPTIMIZED"),
        .CLKFBOUT_MULT_F(CLKFBOUT_MULT_F),
        .CLKFBOUT_PHASE(0.000),
        .CLKIN1_PERIOD(CLKIN1_PERIOD_NS),
        .CLKOUT0_DIVIDE_F(CLKOUT0_DIVIDE_F),
        .CLKOUT0_DUTY_CYCLE(0.500),
        .CLKOUT0_PHASE(0.000),
        .DIVCLK_DIVIDE(DIVCLK_DIVIDE),
        .IS_CLKIN1_INVERTED(1'b0),
        .IS_PWRDWN_INVERTED(1'b0),
        .IS_RST_INVERTED(1'b0),
        .REF_JITTER1(0.010),
        .STARTUP_WAIT("FALSE")
      ) u_mmcm (
        .CLKOUT0(clkout0_mmcm),
        .CLKOUT0B(),
        .CLKOUT1(),
        .CLKOUT1B(),
        .CLKOUT2(),
        .CLKOUT2B(),
        .CLKOUT3(),
        .CLKOUT3B(),
        .CLKOUT4(),
        .CLKOUT5(),
        .CLKOUT6(),
        .CLKFBOUT(clkfb_mmcm),
        .CLKFBOUTB(),
        .LOCKED(mmcm_locked),
        .CLKIN1(clk_ibuf),
        .PWRDWN(1'b0),
        .RST(!rst_ni),
        .CLKFBIN(clkfb_buf)
      );

      BUFG u_clkfb_buf (
        .I(clkfb_mmcm),
        .O(clkfb_buf)
      );

      BUFG u_clkout_buf (
        .I(clkout0_mmcm),
        .O(clk_o)
      );

      assign locked_o = mmcm_locked;
    end
  endgenerate
`endif
endmodule

`default_nettype wire
