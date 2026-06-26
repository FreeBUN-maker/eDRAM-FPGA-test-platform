import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge

EDRAM_REQ_WRITE_ROW = 1
EDRAM_REQ_READ_GROUP = 2


def pack_bytes(values):
    packed = 0
    for index, value in enumerate(values):
        packed |= int(value) << (index * 8)
    return packed


async def reset(dut):
    dut.rst_ni.value = 0
    dut.soft_reset_i.value = 0
    dut.req_valid_i.value = 0
    dut.req_op_i.value = 0
    dut.req_row_i.value = 0
    dut.req_group_i.value = 0
    dut.req_write_data_i.value = 0
    dut.edram_p_i.value = 0
    await ClockCycles(dut.clk_i, 3)
    dut.rst_ni.value = 1
    await ClockCycles(dut.clk_i, 2)


async def tick(dut):
    await RisingEdge(dut.clk_i)
    await ReadOnly()
    sample = {
        "ready": int(dut.req_ready_o.value),
        "done": int(dut.done_o.value),
        "timeout": int(dut.timeout_o.value),
        "busy": int(dut.busy_o.value),
        "read_data": int(dut.read_data_o.value),
        "load_n": int(dut.edram_load_n_o.value),
        "read_n": int(dut.edram_read_n_o.value),
        "en_wwl_n": int(dut.edram_en_wwl_n_o.value),
        "en_rwl_n": int(dut.edram_en_rwl_n_o.value),
        "wg": int(dut.edram_wg_o.value),
        "rg": int(dut.edram_rg_o.value),
        "din": int(dut.edram_din_o.value),
        "a": int(dut.edram_a_o.value),
        "w": int(dut.edram_w_o.value),
    }
    await NextTimeStep()
    return sample


def assert_idle(sample):
    assert sample["load_n"] == 1
    assert sample["read_n"] == 1
    assert sample["en_wwl_n"] == 1
    assert sample["en_rwl_n"] == 1
    assert sample["wg"] == 0
    assert sample["rg"] == 0
    assert sample["din"] == 0
    assert sample["a"] == 0
    assert sample["w"] == 0


async def start_req(dut, op, row, group=0, data=0):
    dut.req_op_i.value = op
    dut.req_row_i.value = row
    dut.req_group_i.value = group
    dut.req_write_data_i.value = data
    dut.req_valid_i.value = 1
    sample = await tick(dut)
    dut.req_valid_i.value = 0
    return sample


@cocotb.test()
async def write_row_timing(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)
    sample = await tick(dut)
    assert_idle(sample)
    assert sample["ready"] == 1

    data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    sample = await start_req(dut, EDRAM_REQ_WRITE_ROW, row=0x0C, data=pack_bytes(data))

    for group, value in enumerate(data):
        assert sample["wg"] == group
        assert sample["din"] == value
        assert sample["load_n"] == 1
        assert sample["read_n"] == 1
        assert sample["en_rwl_n"] == 1

        sample = await tick(dut)
        assert sample["wg"] == group
        assert sample["din"] == value
        assert sample["load_n"] == 0

        sample = await tick(dut)
        assert sample["wg"] == group
        assert sample["din"] == value
        assert sample["load_n"] == 1

        sample = await tick(dut)

    assert sample["a"] == 0x0C
    assert sample["en_wwl_n"] == 1
    sample = await tick(dut)
    assert sample["a"] == 0x0C
    assert sample["en_wwl_n"] == 0
    sample = await tick(dut)
    assert sample["a"] == 0x0C
    assert sample["en_wwl_n"] == 1
    sample = await tick(dut)
    assert sample["done"] == 1
    assert_idle(sample)


@cocotb.test()
async def read_group_timing_and_sample(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    dut.edram_p_i.value = 0x5A
    sample = await start_req(dut, EDRAM_REQ_READ_GROUP, row=0x0C, group=0x03)
    assert sample["w"] == 0x0C
    assert sample["rg"] == 0x03
    assert sample["read_n"] == 0
    assert sample["en_rwl_n"] == 1
    assert sample["load_n"] == 1
    assert sample["en_wwl_n"] == 1

    sample = await tick(dut)
    assert sample["read_n"] == 0
    assert sample["en_rwl_n"] == 0
    sample = await tick(dut)
    assert sample["read_n"] == 0
    assert sample["en_rwl_n"] == 0
    sample = await tick(dut)
    assert sample["read_n"] == 1
    assert sample["en_rwl_n"] == 1
    assert sample["read_data"] == 0x5A
    sample = await tick(dut)
    assert sample["done"] == 1
    assert_idle(sample)


@cocotb.test()
async def soft_reset_returns_idle(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    sample = await start_req(dut, EDRAM_REQ_WRITE_ROW, row=0x02, data=pack_bytes([1] * 8))
    assert sample["busy"] == 1
    dut.soft_reset_i.value = 1
    sample = await tick(dut)
    dut.soft_reset_i.value = 0
    assert sample["busy"] == 0
    assert_idle(sample)
