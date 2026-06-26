import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge

from protocol import (
    OP_PING,
    OP_READ_GROUP,
    OP_READ_ROW,
    OP_RESET,
    OP_STATUS,
    OP_WRITE_ROW,
    STAT_ACK,
    STAT_NACK_BAD_OP,
    STAT_NACK_BUSY,
    STAT_NACK_TIMEOUT,
)

EDRAM_REQ_WRITE_ROW = 1
EDRAM_REQ_READ_GROUP = 2


def pack_args(values):
    packed = 0
    for index, value in enumerate(values):
        packed |= int(value) << (index * 8)
    return packed


def unpack_bytes(value, count):
    return [(int(value) >> (index * 8)) & 0xFF for index in range(count)]


async def reset(dut):
    dut.rst_ni.value = 0
    dut.cmd_valid_i.value = 0
    dut.cmd_op_i.value = 0
    dut.cmd_len_i.value = 0
    dut.cmd_args_i.value = 0
    dut.parse_err_valid_i.value = 0
    dut.parse_err_status_i.value = 0
    dut.parse_err_op_i.value = 0
    dut.resp_ready_i.value = 1
    dut.edram_req_ready_i.value = 1
    dut.edram_busy_i.value = 0
    dut.edram_done_i.value = 0
    dut.edram_timeout_i.value = 0
    dut.edram_read_data_i.value = 0
    await ClockCycles(dut.clk_i, 3)
    dut.rst_ni.value = 1
    await ClockCycles(dut.clk_i, 2)


async def tick(dut):
    await RisingEdge(dut.clk_i)
    await ReadOnly()
    sample = {
        "resp_valid": int(dut.resp_valid_o.value),
        "resp_status": int(dut.resp_status_o.value),
        "resp_op": int(dut.resp_op_o.value),
        "resp_len": int(dut.resp_data_len_o.value),
        "resp_data": int(dut.resp_data_o.value),
        "req_valid": int(dut.edram_req_valid_o.value),
        "req_op": int(dut.edram_req_op_o.value),
        "req_row": int(dut.edram_req_row_o.value),
        "req_group": int(dut.edram_req_group_o.value),
        "req_data": int(dut.edram_req_write_data_o.value),
        "soft_reset": int(dut.edram_soft_reset_o.value),
    }
    await NextTimeStep()
    return sample


async def pulse_cmd(dut, op, length, args=()):
    dut.cmd_op_i.value = op
    dut.cmd_len_i.value = length
    dut.cmd_args_i.value = pack_args(args)
    dut.cmd_valid_i.value = 1
    sample = await tick(dut)
    dut.cmd_valid_i.value = 0
    return sample


async def accept_response(dut):
    assert int(dut.resp_ready_i.value) == 1
    await tick(dut)


@cocotb.test()
async def control_and_error_responses(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    sample = await pulse_cmd(dut, OP_PING, 1)
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert sample["resp_op"] == OP_PING
    assert sample["resp_len"] == 1
    assert unpack_bytes(sample["resp_data"], 1) == [0xA5]
    assert sample["req_valid"] == 0
    await accept_response(dut)

    sample = await pulse_cmd(dut, 0x99, 1)
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_NACK_BAD_OP
    assert sample["resp_op"] == 0x99
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_STATUS, 1)
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert unpack_bytes(sample["resp_data"], 2) == [0x00, STAT_NACK_BAD_OP]
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_RESET, 1)
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert sample["soft_reset"] == 1
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_STATUS, 1)
    assert sample["resp_valid"] == 1
    assert unpack_bytes(sample["resp_data"], 2) == [0x00, 0x00]


@cocotb.test()
async def edram_dispatch_and_busy_timeout(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    row_data = [0x0C, 0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    sample = await pulse_cmd(dut, OP_WRITE_ROW, 10, row_data)
    assert sample["req_valid"] == 1
    assert sample["req_op"] == EDRAM_REQ_WRITE_ROW
    assert sample["req_row"] == 0x0C
    assert unpack_bytes(sample["req_data"], 8) == row_data[1:]

    await tick(dut)
    dut.edram_done_i.value = 1
    sample = await tick(dut)
    dut.edram_done_i.value = 0
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert sample["resp_op"] == OP_WRITE_ROW
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_READ_GROUP, 3, [0x0D, 0x03])
    assert sample["req_valid"] == 1
    assert sample["req_op"] == EDRAM_REQ_READ_GROUP
    assert sample["req_row"] == 0x0D
    assert sample["req_group"] == 0x03
    await tick(dut)
    dut.edram_read_data_i.value = 0x5A
    dut.edram_done_i.value = 1
    sample = await tick(dut)
    dut.edram_done_i.value = 0
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert unpack_bytes(sample["resp_data"], 1) == [0x5A]
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_READ_ROW, 2, [0x0E])
    for group in range(8):
        assert sample["req_valid"] == 1
        assert sample["req_op"] == EDRAM_REQ_READ_GROUP
        assert sample["req_group"] == group
        await tick(dut)
        dut.edram_read_data_i.value = 0x20 + group
        dut.edram_done_i.value = 1
        sample = await tick(dut)
        dut.edram_done_i.value = 0
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_ACK
    assert unpack_bytes(sample["resp_data"], 8) == [0x20 + i for i in range(8)]
    await accept_response(dut)

    dut.edram_busy_i.value = 1
    dut.edram_req_ready_i.value = 0
    sample = await pulse_cmd(dut, OP_WRITE_ROW, 10, row_data)
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_NACK_BUSY
    assert sample["req_valid"] == 0
    dut.edram_busy_i.value = 0
    dut.edram_req_ready_i.value = 1
    await accept_response(dut)

    sample = await pulse_cmd(dut, OP_READ_GROUP, 3, [0x0D, 0x02])
    assert sample["req_valid"] == 1
    await tick(dut)
    dut.edram_timeout_i.value = 1
    sample = await tick(dut)
    dut.edram_timeout_i.value = 0
    assert sample["resp_valid"] == 1
    assert sample["resp_status"] == STAT_NACK_TIMEOUT
