SOF_REQ = 0x55
SOF_RESP = 0xAA

OP_PING = 0x00
OP_WRITE_ROW = 0x01
OP_READ_GROUP = 0x02
OP_READ_ROW = 0x03
OP_RESET = 0x04
OP_STATUS = 0x05

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


def self_test():
    data = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77]
    assert build_request(OP_PING) == [0x55, 0x01, 0x00, 0x01]
    assert build_response(STAT_ACK, OP_PING, [0xA5]) == [0xAA, 0x03, 0x00, 0x00, 0xA5, 0xA6]
    assert write_row_frame(0x0C, data) == [
        0x55, 0x0A, 0x01, 0x0C, 0x00, 0x11, 0x22,
        0x33, 0x44, 0x55, 0x66, 0x77, 0x07,
    ]
    assert build_response(STAT_ACK, OP_WRITE_ROW) == [0xAA, 0x02, 0x00, 0x01, 0x03]
    assert read_group_frame(0x0C, 0x03) == [0x55, 0x03, 0x02, 0x0C, 0x03, 0x0E]
    assert build_response(STAT_ACK, OP_READ_GROUP, [0x5A]) == [0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B]
    assert read_row_frame(0x0C) == [0x55, 0x02, 0x03, 0x0C, 0x0D]
    assert build_request(OP_RESET) == [0x55, 0x01, 0x04, 0x05]
    assert build_request(OP_STATUS) == [0x55, 0x01, 0x05, 0x04]
    assert build_response(STAT_ACK, OP_STATUS, [0x00, 0x00]) == [
        0xAA, 0x04, 0x00, 0x05, 0x00, 0x00, 0x01,
    ]
    parsed = parse_response([0xAA, 0x03, 0x00, 0x02, 0x5A, 0x5B])
    assert parsed == {"status": STAT_ACK, "op": OP_READ_GROUP, "data": [0x5A]}


if __name__ == "__main__":
    self_test()
    print("protocol examples OK")
