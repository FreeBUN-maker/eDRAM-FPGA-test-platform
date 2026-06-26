import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, NextTimeStep, ReadOnly, RisingEdge, with_timeout

from protocol import (
    OP_READ_GROUP,
    OP_READ_ROW,
    OP_WRITE_ROW,
    STAT_ACK,
    build_response,
    parse_response,
    read_group_frame,
    read_row_frame,
    write_row_frame,
)

BIT_CYCLES = 10


async def reset(dut):
    dut.rst_ni.value = 0
    dut.uart_rx_i.value = 1
    dut.edram_p_i.value = 0
    await ClockCycles(dut.clk_i, 5)
    dut.rst_ni.value = 1
    await ClockCycles(dut.clk_i, 5)


async def send_uart_byte(dut, byte):
    dut.uart_rx_i.value = 0
    await ClockCycles(dut.clk_i, BIT_CYCLES)
    for bit in range(8):
        dut.uart_rx_i.value = (byte >> bit) & 1
        await ClockCycles(dut.clk_i, BIT_CYCLES)
    dut.uart_rx_i.value = 1
    await ClockCycles(dut.clk_i, BIT_CYCLES)


async def send_uart_frame(dut, frame):
    for byte in frame:
        await send_uart_byte(dut, byte)


async def recv_uart_byte(dut):
    await with_timeout(FallingEdge(dut.uart_tx_o), 5000, "us")
    await ClockCycles(dut.clk_i, BIT_CYCLES + BIT_CYCLES // 2)
    value = 0
    for bit in range(8):
        await ReadOnly()
        value |= int(dut.uart_tx_o.value) << bit
        await NextTimeStep()
        await ClockCycles(dut.clk_i, BIT_CYCLES)
    await ReadOnly()
    assert int(dut.uart_tx_o.value) == 1
    await NextTimeStep()
    return value


async def recv_response(dut):
    sof = await recv_uart_byte(dut)
    length = await recv_uart_byte(dut)
    rest = [await recv_uart_byte(dut) for _ in range(length + 1)]
    frame = [sof, length, *rest]
    parse_response(frame)
    return frame


async def edram_read_model(dut):
    while True:
        await RisingEdge(dut.clk_i)
        if int(dut.edram_read_n_o.value) == 0:
            group = int(dut.edram_rg_o.value)
            dut.edram_p_i.value = 0x30 + group


@cocotb.test()
async def uart_write_read_group_and_read_row(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    cocotb.start_soon(edram_read_model(dut))
    await reset(dut)

    row_data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    await send_uart_frame(dut, write_row_frame(0x0C, row_data))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_WRITE_ROW)

    await send_uart_frame(dut, read_group_frame(0x0C, 0x03))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_READ_GROUP, [0x33])

    await send_uart_frame(dut, read_row_frame(0x0C))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_READ_ROW, [0x30 + i for i in range(8)])
