import cocotb
from cocotb.triggers import ClockCycles, FallingEdge, NextTimeStep, ReadOnly, RisingEdge, Timer


async def drive_diff_clock(dut, half_period_ns=5):
    dut.clk_p_i.value = 0
    dut.clk_n_i.value = 1
    while True:
        await Timer(half_period_ns, units="ns")
        dut.clk_p_i.value = 1
        dut.clk_n_i.value = 0
        await Timer(half_period_ns, units="ns")
        dut.clk_p_i.value = 0
        dut.clk_n_i.value = 1


@cocotb.test()
async def sim_bypass_forwards_clock_and_locks_after_reset(dut):
    cocotb.start_soon(drive_diff_clock(dut))

    dut.rst_ni.value = 0
    await ClockCycles(dut.clk_p_i, 2)
    await ReadOnly()
    assert int(dut.locked_o.value) == 0

    await FallingEdge(dut.clk_p_i)
    await ReadOnly()
    assert int(dut.clk_o.value) == 0
    await NextTimeStep()

    dut.rst_ni.value = 1

    await RisingEdge(dut.clk_p_i)
    await ReadOnly()
    assert int(dut.clk_o.value) == 1
    assert int(dut.locked_o.value) == 0

    await ClockCycles(dut.clk_p_i, 4)
    await ReadOnly()
    assert int(dut.locked_o.value) == 1
