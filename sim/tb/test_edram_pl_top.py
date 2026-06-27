import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, NextTimeStep, ReadOnly, RisingEdge, with_timeout

from protocol import (
    OP_PING,
    OP_READ_GROUP,
    OP_READ_OUTPUTS,
    OP_READ_OUTPUT_TRACE,
    OP_READ_ROW,
    OP_RESET,
    OP_STATUS,
    OP_WRITE_ROW,
    STAT_ACK,
    STAT_NACK_BAD_ARG,
    STAT_NACK_BAD_CHK,
    STAT_NACK_BAD_LEN,
    STAT_NACK_BAD_OP,
    build_request,
    build_response,
    corrupt_checksum,
    decode_output_trace_payload,
    ping_frame,
    pack_output_snapshot,
    parse_response,
    read_group_frame,
    read_outputs_frame,
    read_output_trace_frame,
    read_row_frame,
    reset_frame,
    status_frame,
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


async def recv_parsed_response(dut):
    frame = await recv_response(dut)
    return parse_response(frame)


async def edram_read_model(dut):
    while True:
        await RisingEdge(dut.clk_i)
        if int(dut.edram_read_n_o.value) == 0:
            group = int(dut.edram_rg_o.value)
            dut.edram_p_i.value = 0x30 + group


async def assert_edram_idle(dut):
    await ReadOnly()
    assert int(dut.edram_load_n_o.value) == 1
    assert int(dut.edram_read_n_o.value) == 1
    assert int(dut.edram_en_wwl_n_o.value) == 1
    assert int(dut.edram_en_rwl_n_o.value) == 1
    assert int(dut.edram_wg_o.value) == 0
    assert int(dut.edram_rg_o.value) == 0
    assert int(dut.edram_din_o.value) == 0
    assert int(dut.edram_a_o.value) == 0
    assert int(dut.edram_w_o.value) == 0
    await NextTimeStep()


def find_record_after(records, start_index, predicate):
    for index in range(start_index, len(records)):
        if predicate(records[index]):
            return index + 1
    raise AssertionError("expected output trace record not found")


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


@cocotb.test()
async def uart_control_frames(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    await reset(dut)
    await assert_edram_idle(dut)

    await send_uart_frame(dut, ping_frame())
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_PING, [0xA5])
    await assert_edram_idle(dut)

    await send_uart_frame(dut, status_frame())
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_STATUS, [0x00, 0x00])
    await assert_edram_idle(dut)

    await send_uart_frame(dut, reset_frame())
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_RESET)
    await assert_edram_idle(dut)


@cocotb.test()
async def uart_read_outputs_returns_idle_snapshot(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    await reset(dut)
    await assert_edram_idle(dut)

    await send_uart_frame(dut, read_outputs_frame())
    frame = await recv_response(dut)
    idle_snapshot = pack_output_snapshot(1, 1, 1, 1, 0, 0, 0, 0, 0)
    assert frame == build_response(STAT_ACK, OP_READ_OUTPUTS, idle_snapshot)
    await assert_edram_idle(dut)


@cocotb.test()
async def uart_write_row_output_trace_records_host_intent(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    await reset(dut)

    row = 0x0C
    row_data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    await send_uart_frame(dut, write_row_frame(row, row_data))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_WRITE_ROW)

    await send_uart_frame(dut, read_output_trace_frame(0))
    parsed = await recv_parsed_response(dut)
    assert parsed["status"] == STAT_ACK
    assert parsed["op"] == OP_READ_OUTPUT_TRACE
    first_trace = decode_output_trace_payload(parsed["data"])
    count = first_trace["count"]
    assert count >= 9
    assert first_trace["index"] == 0

    records = [first_trace["snapshot"]]
    for index in range(1, count):
        await send_uart_frame(dut, read_output_trace_frame(index))
        parsed = await recv_parsed_response(dut)
        assert parsed["status"] == STAT_ACK
        trace = decode_output_trace_payload(parsed["data"])
        assert trace["count"] == count
        assert trace["index"] == index
        records.append(trace["snapshot"])

    search_start = 0
    for group, expected in enumerate(row_data):
        search_start = find_record_after(
            records,
            search_start,
            lambda snapshot, group=group, expected=expected: (
                snapshot["load_n"] == 0 and
                snapshot["read_n"] == 1 and
                snapshot["en_wwl_n"] == 1 and
                snapshot["en_rwl_n"] == 1 and
                snapshot["wg"] == group and
                snapshot["din"] == expected
            ),
        )

    find_record_after(
        records,
        search_start,
        lambda snapshot: (
            snapshot["load_n"] == 1 and
            snapshot["read_n"] == 1 and
            snapshot["en_wwl_n"] == 0 and
            snapshot["en_rwl_n"] == 1 and
            snapshot["a"] == row
        ),
    )


@cocotb.test()
async def uart_output_trace_bad_index_returns_nack(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    await reset(dut)

    await send_uart_frame(dut, read_output_trace_frame(0))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_NACK_BAD_ARG, OP_READ_OUTPUT_TRACE)
    await assert_edram_idle(dut)


@cocotb.test()
async def uart_error_frames_return_nacks_and_leave_edram_idle(dut):
    cocotb.start_soon(Clock(dut.clk_i, 1, units="us").start())
    await reset(dut)

    await send_uart_byte(dut, 0x00)
    await send_uart_frame(dut, ping_frame())
    frame = await recv_response(dut)
    assert frame == build_response(STAT_ACK, OP_PING, [0xA5])

    await send_uart_frame(dut, corrupt_checksum(ping_frame()))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_NACK_BAD_CHK, OP_PING)
    await assert_edram_idle(dut)

    await send_uart_frame(dut, build_request(OP_READ_GROUP, [0x0C]))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_NACK_BAD_LEN, OP_READ_GROUP)
    await assert_edram_idle(dut)

    await send_uart_frame(dut, build_request(0x99))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_NACK_BAD_OP, 0x99)
    await assert_edram_idle(dut)

    await send_uart_frame(dut, build_request(OP_READ_GROUP, [0x40, 0x08]))
    frame = await recv_response(dut)
    assert frame == build_response(STAT_NACK_BAD_ARG, OP_READ_GROUP)
    await assert_edram_idle(dut)
