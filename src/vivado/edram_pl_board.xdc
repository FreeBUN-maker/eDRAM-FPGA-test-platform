# AXU5EVB-E board constraints for edram_pl_board_top.
#
# Pin selections mirror src/vivado/config.json. Treat the eDRAM connector
# mapping as a bring-up placeholder until the external eDRAM board cabling and
# electrical requirements have been reviewed.

# 200 MHz PL differential clock, AXU5EVB-E manual page 21.
set_property PACKAGE_PIN AE5 [get_ports {pl_clk0_p_i}]
set_property IOSTANDARD LVDS [get_ports {pl_clk0_p_i}]
set_property PACKAGE_PIN AF5 [get_ports {pl_clk0_n_i}]
set_property IOSTANDARD LVDS [get_ports {pl_clk0_n_i}]
create_clock -name pl_clk0 -period 5.000 [get_ports {pl_clk0_p_i}]

# Active-low PL reset, AXU5EVB-E PL_KEY1, manual page 48.
set_property PACKAGE_PIN AF12 [get_ports {rst_ni}]
set_property IOSTANDARD LVCMOS33 [get_ports {rst_ni}]

# PL USB-UART pins, AXU5EVB-E manual page 40.
set_property PACKAGE_PIN AH11 [get_ports {uart_rx_i}]
set_property IOSTANDARD LVCMOS33 [get_ports {uart_rx_i}]
set_property PACKAGE_PIN AH12 [get_ports {uart_tx_o}]
set_property IOSTANDARD LVCMOS33 [get_ports {uart_tx_o}]

# eDRAM active-low control pins, selected on J16.
set_property PACKAGE_PIN B10 [get_ports {edram_load_n_o}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_load_n_o}]
set_property PACKAGE_PIN C11 [get_ports {edram_read_n_o}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_read_n_o}]
set_property PACKAGE_PIN F10 [get_ports {edram_en_wwl_n_o}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_en_wwl_n_o}]
set_property PACKAGE_PIN G11 [get_ports {edram_en_rwl_n_o}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_en_rwl_n_o}]

# eDRAM write group select, selected on J16.
set_property PACKAGE_PIN C12 [get_ports {edram_wg_o[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_wg_o[0]}]
set_property PACKAGE_PIN D12 [get_ports {edram_wg_o[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_wg_o[1]}]
set_property PACKAGE_PIN A11 [get_ports {edram_wg_o[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_wg_o[2]}]

# eDRAM read group select, selected on J16.
set_property PACKAGE_PIN A12 [get_ports {edram_rg_o[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_rg_o[0]}]
set_property PACKAGE_PIN F11 [get_ports {edram_rg_o[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_rg_o[1]}]
set_property PACKAGE_PIN F12 [get_ports {edram_rg_o[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_rg_o[2]}]

# eDRAM write data, selected on J16.
set_property PACKAGE_PIN E13 [get_ports {edram_din_o[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[0]}]
set_property PACKAGE_PIN E14 [get_ports {edram_din_o[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[1]}]
set_property PACKAGE_PIN A13 [get_ports {edram_din_o[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[2]}]
set_property PACKAGE_PIN B13 [get_ports {edram_din_o[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[3]}]
set_property PACKAGE_PIN A14 [get_ports {edram_din_o[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[4]}]
set_property PACKAGE_PIN B14 [get_ports {edram_din_o[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[5]}]
set_property PACKAGE_PIN C13 [get_ports {edram_din_o[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[6]}]
set_property PACKAGE_PIN C14 [get_ports {edram_din_o[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_din_o[7]}]

# eDRAM write row address, selected on J16.
set_property PACKAGE_PIN L13 [get_ports {edram_a_o[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[0]}]
set_property PACKAGE_PIN L14 [get_ports {edram_a_o[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[1]}]
set_property PACKAGE_PIN H12 [get_ports {edram_a_o[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[2]}]
set_property PACKAGE_PIN J12 [get_ports {edram_a_o[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[3]}]
set_property PACKAGE_PIN J14 [get_ports {edram_a_o[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[4]}]
set_property PACKAGE_PIN K14 [get_ports {edram_a_o[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_a_o[5]}]

# eDRAM read row address, selected on J16.
set_property PACKAGE_PIN H13 [get_ports {edram_w_o[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[0]}]
set_property PACKAGE_PIN H14 [get_ports {edram_w_o[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[1]}]
set_property PACKAGE_PIN F13 [get_ports {edram_w_o[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[2]}]
set_property PACKAGE_PIN G13 [get_ports {edram_w_o[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[3]}]
set_property PACKAGE_PIN G14 [get_ports {edram_w_o[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[4]}]
set_property PACKAGE_PIN G15 [get_ports {edram_w_o[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_w_o[5]}]

# eDRAM readback data, selected on J15.
set_property PACKAGE_PIN AG11 [get_ports {edram_p_i[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[0]}]
set_property PACKAGE_PIN AF11 [get_ports {edram_p_i[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[1]}]
set_property PACKAGE_PIN AB14 [get_ports {edram_p_i[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[2]}]
set_property PACKAGE_PIN AB15 [get_ports {edram_p_i[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[3]}]
set_property PACKAGE_PIN W13 [get_ports {edram_p_i[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[4]}]
set_property PACKAGE_PIN W14 [get_ports {edram_p_i[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[5]}]
set_property PACKAGE_PIN W11 [get_ports {edram_p_i[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[6]}]
set_property PACKAGE_PIN W12 [get_ports {edram_p_i[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {edram_p_i[7]}]
