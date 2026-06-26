import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge

from protocol import (
    OP_PING,
    OP_READ_GROUP,
    OP_WRITE_ROW,
    STAT_NACK_BAD_CHK,
    STAT_NACK_BAD_LEN,
    build_request,
    write_row_frame,
)


async def reset(dut):
    dut.rst_ni.value = 0
    dut.clear_i.value = 0
    dut.byte_i.value = 0
    dut.byte_valid_i.value = 0
    dut.framing_error_i.value = 0
    await ClockCycles(dut.clk_i, 3)
    dut.rst_ni.value = 1
    await ClockCycles(dut.clk_i, 2)


async def pulse_byte(dut, value):
    dut.byte_i.value = value
    dut.byte_valid_i.value = 1
    await RisingEdge(dut.clk_i)
    dut.byte_valid_i.value = 0
    await ReadOnly()
    sample = {
        "cmd_valid": int(dut.cmd_valid_o.value),
        "cmd_op": int(dut.cmd_op_o.value),
        "cmd_len": int(dut.cmd_len_o.value),
        "cmd_args": int(dut.cmd_args_o.value),
        "err_valid": int(dut.parse_err_valid_o.value),
        "err_status": int(dut.parse_err_status_o.value),
        "err_op": int(dut.parse_err_op_o.value),
    }
    await NextTimeStep()
    return sample


async def send_frame(dut, frame):
    sample = None
    for byte in frame:
        sample = await pulse_byte(dut, byte)
    return sample


@cocotb.test()
async def valid_frames_and_parser_errors(dut):
    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    await reset(dut)

    sample = await send_frame(dut, build_request(OP_PING))
    assert sample["cmd_valid"] == 1
    assert sample["cmd_op"] == OP_PING
    assert sample["cmd_len"] == 1
    assert sample["err_valid"] == 0

    await reset(dut)
    data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    sample = await send_frame(dut, write_row_frame(0x0C, data))
    assert sample["cmd_valid"] == 1
    assert sample["cmd_op"] == OP_WRITE_ROW
    assert sample["cmd_len"] == 10
    assert (sample["cmd_args"] & 0xFF) == 0x0C
    for index, value in enumerate(data):
        assert ((sample["cmd_args"] >> ((index + 1) * 8)) & 0xFF) == value

    await reset(dut)
    for byte in [0x00, 0x12, 0xAA]:
        sample = await pulse_byte(dut, byte)
        assert sample["cmd_valid"] == 0
        assert sample["err_valid"] == 0

    sample = await send_frame(dut, [0x55, 0x01, 0x00, 0x00])
    assert sample["cmd_valid"] == 0
    assert sample["err_valid"] == 1
    assert sample["err_status"] == STAT_NACK_BAD_CHK
    assert sample["err_op"] == OP_PING

    await reset(dut)
    sample = await send_frame(dut, [0x55, 0x00])
    assert sample["cmd_valid"] == 0
    assert sample["err_valid"] == 1
    assert sample["err_status"] == STAT_NACK_BAD_LEN
    assert sample["err_op"] == 0x00

    await reset(dut)
    sample = await send_frame(dut, build_request(0x99))
    assert sample["cmd_valid"] == 1
    assert sample["cmd_op"] == 0x99

    await reset(dut)
    sample = await send_frame(dut, build_request(OP_READ_GROUP, [0x40, 0x08]))
    assert sample["cmd_valid"] == 1
    assert sample["cmd_op"] == OP_READ_GROUP
    assert (sample["cmd_args"] & 0xFF) == 0x40
    assert ((sample["cmd_args"] >> 8) & 0xFF) == 0x08
