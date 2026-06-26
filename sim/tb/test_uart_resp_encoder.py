import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge

from protocol import (
    OP_PING,
    STAT_ACK,
    STAT_NACK_BAD_OP,
    build_response,
)


async def reset(dut):
    dut.rst_ni.value = 0
    dut.resp_valid_i.value = 0
    dut.resp_status_i.value = 0
    dut.resp_op_i.value = 0
    dut.resp_data_len_i.value = 0
    dut.resp_data_i.value = 0
    dut.tx_ready_i.value = 1
    await ClockCycles(dut.clk_i, 3)
    dut.rst_ni.value = 1
    await ClockCycles(dut.clk_i, 2)


async def tick(dut):
    await RisingEdge(dut.clk_i)
    await ReadOnly()
    sample = {
        "tx_valid": int(dut.tx_valid_o.value),
        "tx_byte": int(dut.tx_byte_o.value),
        "resp_ready": int(dut.resp_ready_o.value),
        "busy": int(dut.busy_o.value),
    }
    await NextTimeStep()
    return sample


async def collect_response(dut, status, op, data):
    payload = 0
    for index, value in enumerate(data):
        payload |= int(value) << (index * 8)

    dut.resp_status_i.value = status
    dut.resp_op_i.value = op
    dut.resp_data_len_i.value = len(data)
    dut.resp_data_i.value = payload
    dut.resp_valid_i.value = 1

    expected_len = 5 + len(data)
    got = []
    for cycle in range(100):
        sample = await tick(dut)
        if cycle == 0:
            dut.resp_valid_i.value = 0
        if sample["tx_valid"]:
            got.append(sample["tx_byte"])
        if len(got) == expected_len:
            return got
    raise AssertionError("response encoder did not finish")


@cocotb.test()
async def ack_and_nack_response_frames(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    got = await collect_response(dut, STAT_ACK, OP_PING, [0xA5])
    assert got == build_response(STAT_ACK, OP_PING, [0xA5])

    await ClockCycles(dut.clk_i, 2)
    got = await collect_response(dut, STAT_NACK_BAD_OP, 0x99, [])
    assert got == build_response(STAT_NACK_BAD_OP, 0x99)
