import cocotb
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, Timer


async def drive_diff_clock(dut, half_period_ns=5):
    dut.pl_clk0_p_i.value = 0
    dut.pl_clk0_n_i.value = 1
    while True:
        await Timer(half_period_ns, units="ns")
        dut.pl_clk0_p_i.value = 1
        dut.pl_clk0_n_i.value = 0
        await Timer(half_period_ns, units="ns")
        dut.pl_clk0_p_i.value = 0
        dut.pl_clk0_n_i.value = 1


async def sample(dut):
    await ReadOnly()
    values = {
        "clk_locked": int(dut.clk_locked.value),
        "core_rst_ni": int(dut.core_rst_ni.value),
        "core_clk": int(dut.core_clk.value),
        "edram_load_n_o": int(dut.edram_load_n_o.value),
        "edram_read_n_o": int(dut.edram_read_n_o.value),
        "edram_en_wwl_n_o": int(dut.edram_en_wwl_n_o.value),
        "edram_en_rwl_n_o": int(dut.edram_en_rwl_n_o.value),
    }
    return values


@cocotb.test()
async def wrapper_holds_core_reset_until_clock_lock(dut):
    cocotb.start_soon(drive_diff_clock(dut))

    dut.rst_ni.value = 0
    dut.uart_rx_i.value = 1
    dut.edram_p_i.value = 0
    await ClockCycles(dut.pl_clk0_p_i, 5)

    values = await sample(dut)
    assert values["clk_locked"] == 0
    assert values["core_rst_ni"] == 0
    assert values["edram_load_n_o"] == 1
    assert values["edram_read_n_o"] == 1
    assert values["edram_en_wwl_n_o"] == 1
    assert values["edram_en_rwl_n_o"] == 1
    await NextTimeStep()

    dut.rst_ni.value = 1
    await ClockCycles(dut.pl_clk0_p_i, 3)
    values = await sample(dut)
    assert values["clk_locked"] == 0
    assert values["core_rst_ni"] == 0
    await NextTimeStep()

    await ClockCycles(dut.pl_clk0_p_i, 5)
    values = await sample(dut)
    assert values["clk_locked"] == 1
    assert values["core_rst_ni"] == 1


@cocotb.test()
async def wrapper_connects_generated_clock_to_core(dut):
    cocotb.start_soon(drive_diff_clock(dut))

    dut.rst_ni.value = 0
    dut.uart_rx_i.value = 1
    dut.edram_p_i.value = 0
    await ClockCycles(dut.pl_clk0_p_i, 2)
    dut.rst_ni.value = 1
    await ClockCycles(dut.pl_clk0_p_i, 8)

    values = await sample(dut)
    assert values["core_rst_ni"] == 1
    assert values["core_clk"] == int(dut.pl_clk0_p_i.value)
    assert int(dut.u_edram_pl_top.clk_i.value) == values["core_clk"]
    assert int(dut.u_edram_pl_top.rst_ni.value) == 1
