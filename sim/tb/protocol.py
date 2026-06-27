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


def checksum(data):
    value = 0
    for byte in data:
        value ^= int(byte) & 0xFF
    return value


def build_request(op, args=()):
    body = [op, *args]
    length = len(body)
    return [SOF_REQ, length, *body, checksum([length, *body])]


def build_response(status, op, data=()):
    body = [status, op, *data]
    length = len(body)
    return [SOF_RESP, length, *body, checksum([length, *body])]


def ping_frame():
    return build_request(OP_PING)


def reset_frame():
    return build_request(OP_RESET)


def status_frame():
    return build_request(OP_STATUS)


def read_outputs_frame():
    return build_request(OP_READ_OUTPUTS)


def read_output_trace_frame(index):
    if not 0 <= index <= 0xFF:
        raise ValueError("trace index out of range")
    return build_request(OP_READ_OUTPUT_TRACE, [index])


def write_row_frame(row, data_groups):
    if not 0 <= row <= 0x3F:
        raise ValueError("row out of range")
    if len(data_groups) != 8:
        raise ValueError("WRITE_ROW needs exactly 8 data bytes")
    return build_request(OP_WRITE_ROW, [row, *data_groups])


def read_group_frame(row, group):
    if not 0 <= row <= 0x3F:
        raise ValueError("row out of range")
    if not 0 <= group <= 0x07:
        raise ValueError("group out of range")
    return build_request(OP_READ_GROUP, [row, group])


def read_row_frame(row):
    if not 0 <= row <= 0x3F:
        raise ValueError("row out of range")
    return build_request(OP_READ_ROW, [row])


def pack_output_snapshot(load_n, read_n, en_wwl_n, en_rwl_n, wg, rg, din, a, w):
    if load_n not in (0, 1):
        raise ValueError("load_n must be 0 or 1")
    if read_n not in (0, 1):
        raise ValueError("read_n must be 0 or 1")
    if en_wwl_n not in (0, 1):
        raise ValueError("en_wwl_n must be 0 or 1")
    if en_rwl_n not in (0, 1):
        raise ValueError("en_rwl_n must be 0 or 1")
    if not 0 <= wg <= 0x07:
        raise ValueError("wg out of range")
    if not 0 <= rg <= 0x07:
        raise ValueError("rg out of range")
    if not 0 <= din <= 0xFF:
        raise ValueError("din out of range")
    if not 0 <= a <= 0x3F:
        raise ValueError("a out of range")
    if not 0 <= w <= 0x3F:
        raise ValueError("w out of range")
    return [
        load_n | (read_n << 1) | (en_wwl_n << 2) | (en_rwl_n << 3),
        wg | (rg << 3),
        din,
        a,
        w,
    ]


def decode_output_snapshot(data):
    data = list(data)
    if len(data) != 5:
        raise ValueError("snapshot needs exactly 5 bytes")
    s0, s1, din, a, w = data
    if s0 & 0xF0 or s1 & 0xC0 or a & 0xC0 or w & 0xC0:
        raise ValueError("snapshot reserved bits are non-zero")
    return {
        "load_n": s0 & 0x01,
        "read_n": (s0 >> 1) & 0x01,
        "en_wwl_n": (s0 >> 2) & 0x01,
        "en_rwl_n": (s0 >> 3) & 0x01,
        "wg": s1 & 0x07,
        "rg": (s1 >> 3) & 0x07,
        "din": din,
        "a": a & 0x3F,
        "w": w & 0x3F,
        "raw": data,
    }


def decode_output_trace_payload(data):
    data = list(data)
    if len(data) != 7:
        raise ValueError("trace payload needs exactly 7 bytes")
    return {
        "count": data[0],
        "index": data[1],
        "snapshot": decode_output_snapshot(data[2:]),
    }


def parse_response(frame):
    frame = list(frame)
    if len(frame) < 4:
        raise ValueError("response too short")
    if frame[0] != SOF_RESP:
        raise ValueError("bad response SOF")
    length = frame[1]
    if len(frame) != length + 3:
        raise ValueError("bad response length")
    body = frame[2:2 + length]
    got = frame[-1]
    exp = checksum([length, *body])
    if got != exp:
        raise ValueError(f"bad response checksum: got 0x{got:02x}, expected 0x{exp:02x}")
    status, op_echo, *data = body
    return {"status": status, "op": op_echo, "data": data}


def corrupt_checksum(frame):
    frame = list(frame)
    frame[-1] ^= 0xFF
    return frame


def self_test():
    data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    assert ping_frame() == [0x55, 0x01, 0x00, 0x01]
    assert build_response(STAT_ACK, OP_PING, [0xA5]) == [0xAA, 0x03, 0x00, 0x00, 0xA5, 0xA6]
    assert write_row_frame(0x0C, data) == [
        0x55, 0x0A, 0x01, 0x0C, 0x00, 0x11, 0x22,
        0x33, 0x44, 0x55, 0x66, 0x77, 0x07,
    ]
    assert build_response(STAT_ACK, OP_WRITE_ROW) == [0xAA, 0x02, 0x00, 0x01, 0x03]
    assert read_group_frame(0x0C, 0x03) == [0x55, 0x03, 0x02, 0x0C, 0x03, 0x0E]
    assert build_response(STAT_ACK, OP_READ_GROUP, [0x5A]) == [0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B]
    assert read_row_frame(0x0C) == [0x55, 0x02, 0x03, 0x0C, 0x0D]
    assert reset_frame() == [0x55, 0x01, 0x04, 0x05]
    assert status_frame() == [0x55, 0x01, 0x05, 0x04]
    assert read_outputs_frame() == [0x55, 0x01, 0x06, 0x07]
    assert read_output_trace_frame(2) == [0x55, 0x02, 0x07, 0x02, 0x07]
    assert build_response(STAT_ACK, OP_STATUS, [0x00, 0x00]) == [
        0xAA, 0x04, 0x00, 0x05, 0x00, 0x00, 0x01,
    ]
    idle_snapshot = pack_output_snapshot(1, 1, 1, 1, 0, 0, 0, 0, 0)
    assert idle_snapshot == [0x0F, 0x00, 0x00, 0x00, 0x00]
    assert build_response(STAT_ACK, OP_READ_OUTPUTS, idle_snapshot) == [
        0xAA, 0x07, 0x00, 0x06, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x0E,
    ]
    trace = decode_output_trace_payload(
        [9, 2, *pack_output_snapshot(0, 1, 1, 1, 2, 0, 0x22, 0, 0)]
    )
    assert trace["count"] == 9
    assert trace["index"] == 2
    assert trace["snapshot"]["wg"] == 2
    assert trace["snapshot"]["din"] == 0x22
    parsed = parse_response([0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B])
    assert parsed == {"status": STAT_ACK, "op": OP_READ_GROUP, "data": [0x5A]}


if __name__ == "__main__":
    self_test()
    print("protocol examples OK")
