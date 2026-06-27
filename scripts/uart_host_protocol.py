#!/usr/bin/env python3
"""Host-side helpers for the FPGA eDRAM UART protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


DEFAULT_BAUD = 115200

SOF_REQ = 0x55
SOF_RESP = 0xAA

OP_PING = 0x00
OP_WRITE_ROW = 0x01
OP_READ_GROUP = 0x02
OP_READ_ROW = 0x03
OP_RESET = 0x04
OP_STATUS = 0x05
OP_READ_OUTPUTS = 0x06
OP_READ_OUTPUT_TRACE = 0x07

STAT_ACK = 0x00
STAT_NACK_BAD_LEN = 0x01
STAT_NACK_BAD_CHK = 0x02
STAT_NACK_BAD_OP = 0x03
STAT_NACK_BAD_ARG = 0x04
STAT_NACK_BUSY = 0x05
STAT_NACK_TIMEOUT = 0x06

PING_RESP_DATA = 0xA5

EDRAM_ROW_COUNT = 64
EDRAM_GROUP_COUNT = 8
EDRAM_ROW_BYTES = 8
EDRAM_OUTPUT_SNAPSHOT_BYTES = 5
EDRAM_OUTPUT_TRACE_RESP_BYTES = 2 + EDRAM_OUTPUT_SNAPSHOT_BYTES

OP_NAMES = {
    OP_PING: "PING",
    OP_WRITE_ROW: "WRITE_ROW",
    OP_READ_GROUP: "READ_GROUP",
    OP_READ_ROW: "READ_ROW",
    OP_RESET: "RESET",
    OP_STATUS: "STATUS",
    OP_READ_OUTPUTS: "READ_OUTPUTS",
    OP_READ_OUTPUT_TRACE: "READ_OUTPUT_TRACE",
}

STATUS_NAMES = {
    STAT_ACK: "ACK",
    STAT_NACK_BAD_LEN: "NACK_BAD_LEN",
    STAT_NACK_BAD_CHK: "NACK_BAD_CHK",
    STAT_NACK_BAD_OP: "NACK_BAD_OP",
    STAT_NACK_BAD_ARG: "NACK_BAD_ARG",
    STAT_NACK_BUSY: "NACK_BUSY",
    STAT_NACK_TIMEOUT: "NACK_TIMEOUT",
}


class UartProtocolError(ValueError):
    """Raised when a UART protocol frame is malformed."""


@dataclass(frozen=True)
class Response:
    status: int
    op: int
    data: tuple[int, ...]
    raw: bytes

    @property
    def ok(self) -> bool:
        return self.status == STAT_ACK

    @property
    def status_name(self) -> str:
        return status_name(self.status)

    @property
    def op_name(self) -> str:
        return op_name(self.op)


@dataclass(frozen=True)
class OutputSnapshot:
    load_n: int
    read_n: int
    en_wwl_n: int
    en_rwl_n: int
    wg: int
    rg: int
    din: int
    a: int
    w: int
    raw: tuple[int, ...]

    def summary(self) -> str:
        return (
            f"LOAD_N={self.load_n} READ_N={self.read_n} "
            f"EN_WWL_N={self.en_wwl_n} EN_RWL_N={self.en_rwl_n} "
            f"WG={self.wg} RG={self.rg} DIN=0x{self.din:02X} "
            f"A={self.a} W={self.w}"
        )


def _byte(value: int, name: str = "byte") -> int:
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer byte") from exc
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} out of range: {value}")
    return value


def _bit(value: int, name: str = "bit") -> int:
    value = _byte(value, name)
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _bytes(values: Iterable[int], name: str = "byte") -> bytes:
    return bytes(_byte(value, name) for value in values)


def checksum(data: Iterable[int]) -> int:
    value = 0
    for byte in data:
        value ^= _byte(byte)
    return value & 0xFF


def format_bytes(values: Iterable[int]) -> str:
    return " ".join(f"{byte:02X}" for byte in _bytes(values))


def op_name(op: int) -> str:
    op = _byte(op, "op")
    return OP_NAMES.get(op, f"UNKNOWN_OP_0x{op:02X}")


def status_name(status: int) -> str:
    status = _byte(status, "status")
    return STATUS_NAMES.get(status, f"UNKNOWN_STATUS_0x{status:02X}")


def validate_row(row: int) -> int:
    row = int(row)
    if not 0 <= row < EDRAM_ROW_COUNT:
        raise ValueError(f"row out of range: {row} (expected 0..{EDRAM_ROW_COUNT - 1})")
    return row


def validate_group(group: int) -> int:
    group = int(group)
    if not 0 <= group < EDRAM_GROUP_COUNT:
        raise ValueError(f"group out of range: {group} (expected 0..{EDRAM_GROUP_COUNT - 1})")
    return group


def build_request(op: int, args: Sequence[int] = ()) -> bytes:
    op = _byte(op, "op")
    body = bytes([op]) + _bytes(args, "argument")
    length = len(body)
    return bytes([SOF_REQ, length]) + body + bytes([checksum([length, *body])])


def build_response(status: int, op: int, data: Sequence[int] = ()) -> bytes:
    status = _byte(status, "status")
    op = _byte(op, "op")
    body = bytes([status, op]) + _bytes(data, "data")
    length = len(body)
    return bytes([SOF_RESP, length]) + body + bytes([checksum([length, *body])])


def ping_frame() -> bytes:
    return build_request(OP_PING)


def reset_frame() -> bytes:
    return build_request(OP_RESET)


def status_frame() -> bytes:
    return build_request(OP_STATUS)


def write_row_frame(row: int, data_groups: Sequence[int]) -> bytes:
    row = validate_row(row)
    if len(data_groups) != EDRAM_ROW_BYTES:
        raise ValueError(f"WRITE_ROW needs exactly {EDRAM_ROW_BYTES} data bytes")
    return build_request(OP_WRITE_ROW, [row, *_bytes(data_groups, "data")])


def read_group_frame(row: int, group: int) -> bytes:
    return build_request(OP_READ_GROUP, [validate_row(row), validate_group(group)])


def read_row_frame(row: int) -> bytes:
    return build_request(OP_READ_ROW, [validate_row(row)])


def read_outputs_frame() -> bytes:
    return build_request(OP_READ_OUTPUTS)


def read_output_trace_frame(index: int) -> bytes:
    return build_request(OP_READ_OUTPUT_TRACE, [_byte(index, "trace index")])


def pack_output_snapshot(
    *,
    load_n: int,
    read_n: int,
    en_wwl_n: int,
    en_rwl_n: int,
    wg: int,
    rg: int,
    din: int,
    a: int,
    w: int,
) -> tuple[int, ...]:
    wg = validate_group(wg)
    rg = validate_group(rg)
    din = _byte(din, "din")
    a = validate_row(a)
    w = validate_row(w)
    s0 = (
        _bit(load_n, "load_n") |
        (_bit(read_n, "read_n") << 1) |
        (_bit(en_wwl_n, "en_wwl_n") << 2) |
        (_bit(en_rwl_n, "en_rwl_n") << 3)
    )
    s1 = wg | (rg << 3)
    return (s0, s1, din, a, w)


def decode_output_snapshot(data: Iterable[int]) -> OutputSnapshot:
    raw = tuple(_bytes(data, "snapshot"))
    if len(raw) != EDRAM_OUTPUT_SNAPSHOT_BYTES:
        raise UartProtocolError(
            f"output snapshot needs {EDRAM_OUTPUT_SNAPSHOT_BYTES} byte(s), got {len(raw)}"
        )
    s0, s1, din, a, w = raw
    if s0 & 0xF0:
        raise UartProtocolError(f"snapshot S0 reserved bits are non-zero: 0x{s0:02X}")
    if s1 & 0xC0:
        raise UartProtocolError(f"snapshot S1 reserved bits are non-zero: 0x{s1:02X}")
    if a & 0xC0:
        raise UartProtocolError(f"snapshot S3 reserved bits are non-zero: 0x{a:02X}")
    if w & 0xC0:
        raise UartProtocolError(f"snapshot S4 reserved bits are non-zero: 0x{w:02X}")
    return OutputSnapshot(
        load_n=s0 & 0x01,
        read_n=(s0 >> 1) & 0x01,
        en_wwl_n=(s0 >> 2) & 0x01,
        en_rwl_n=(s0 >> 3) & 0x01,
        wg=s1 & 0x07,
        rg=(s1 >> 3) & 0x07,
        din=din,
        a=a & 0x3F,
        w=w & 0x3F,
        raw=raw,
    )


def decode_output_trace_payload(data: Iterable[int]) -> tuple[int, int, OutputSnapshot]:
    raw = tuple(_bytes(data, "trace payload"))
    if len(raw) != EDRAM_OUTPUT_TRACE_RESP_BYTES:
        raise UartProtocolError(
            f"output trace payload needs {EDRAM_OUTPUT_TRACE_RESP_BYTES} byte(s), got {len(raw)}"
        )
    count, index, *snapshot = raw
    return count, index, decode_output_snapshot(snapshot)


def parse_response(frame: Iterable[int]) -> Response:
    raw = _bytes(frame)
    if len(raw) < 3:
        raise UartProtocolError(f"response too short: {format_bytes(raw)}")
    if raw[0] != SOF_RESP:
        raise UartProtocolError(
            f"bad response SOF: got 0x{raw[0]:02X}, expected 0x{SOF_RESP:02X}"
        )

    length = raw[1]
    if length < 2:
        raise UartProtocolError(f"bad response length field: {length} (minimum 2)")

    expected_total = length + 3
    if len(raw) != expected_total:
        raise UartProtocolError(
            f"bad response length: got {len(raw)} byte(s), expected {expected_total}"
        )

    body = raw[2 : 2 + length]
    got = raw[-1]
    expected = checksum([length, *body])
    if got != expected:
        raise UartProtocolError(
            f"bad response checksum: got 0x{got:02X}, expected 0x{expected:02X}"
        )

    status, op, *data = body
    return Response(status=status, op=op, data=tuple(data), raw=raw)


def corrupt_checksum(frame: Iterable[int]) -> bytes:
    data = bytearray(_bytes(frame))
    if not data:
        raise ValueError("cannot corrupt an empty frame")
    data[-1] ^= 0xFF
    return bytes(data)


def self_test() -> None:
    doc_data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]

    assert ping_frame() == bytes([0x55, 0x01, 0x00, 0x01])
    assert build_response(STAT_ACK, OP_PING, [PING_RESP_DATA]) == bytes(
        [0xAA, 0x03, 0x00, 0x00, 0xA5, 0xA6]
    )
    assert write_row_frame(0x0C, doc_data) == bytes(
        [0x55, 0x0A, 0x01, 0x0C, 0x00, 0x11, 0x22,
         0x33, 0x44, 0x55, 0x66, 0x77, 0x07]
    )
    assert build_response(STAT_ACK, OP_WRITE_ROW) == bytes([0xAA, 0x02, 0x00, 0x01, 0x03])
    assert read_group_frame(0x0C, 0x03) == bytes([0x55, 0x03, 0x02, 0x0C, 0x03, 0x0E])
    assert build_response(STAT_ACK, OP_READ_GROUP, [0x5A]) == bytes(
        [0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B]
    )
    assert read_row_frame(0x0C) == bytes([0x55, 0x02, 0x03, 0x0C, 0x0D])
    assert reset_frame() == bytes([0x55, 0x01, 0x04, 0x05])
    assert status_frame() == bytes([0x55, 0x01, 0x05, 0x04])
    assert read_outputs_frame() == bytes([0x55, 0x01, 0x06, 0x07])
    assert read_output_trace_frame(0x02) == bytes([0x55, 0x02, 0x07, 0x02, 0x07])
    assert build_response(STAT_ACK, OP_STATUS, [0x00, 0x00]) == bytes(
        [0xAA, 0x04, 0x00, 0x05, 0x00, 0x00, 0x01]
    )
    idle_snapshot = pack_output_snapshot(
        load_n=1,
        read_n=1,
        en_wwl_n=1,
        en_rwl_n=1,
        wg=0,
        rg=0,
        din=0,
        a=0,
        w=0,
    )
    assert idle_snapshot == (0x0F, 0x00, 0x00, 0x00, 0x00)
    assert build_response(STAT_ACK, OP_READ_OUTPUTS, idle_snapshot) == bytes(
        [0xAA, 0x07, 0x00, 0x06, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x0E]
    )
    active_snapshot = pack_output_snapshot(
        load_n=0,
        read_n=1,
        en_wwl_n=1,
        en_rwl_n=1,
        wg=2,
        rg=0,
        din=0x22,
        a=0,
        w=0,
    )
    count, index, decoded = decode_output_trace_payload((9, 2, *active_snapshot))
    assert (count, index) == (9, 2)
    assert decoded.wg == 2
    assert decoded.din == 0x22
    assert decoded.load_n == 0

    parsed = parse_response([0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B])
    assert parsed.status == STAT_ACK
    assert parsed.op == OP_READ_GROUP
    assert parsed.data == (0x5A,)
    assert parsed.raw == bytes([0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B])

    for bad in (
        [0x55, 0x03, 0x00, 0x02, 0x5A, 0x5B],
        [0xAA, 0x01, 0x00, 0x01],
        corrupt_checksum([0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B]),
    ):
        try:
            parse_response(bad)
        except UartProtocolError:
            pass
        else:
            raise AssertionError(f"malformed response accepted: {format_bytes(bad)}")


def main() -> int:
    self_test()
    print("UART protocol helper self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
