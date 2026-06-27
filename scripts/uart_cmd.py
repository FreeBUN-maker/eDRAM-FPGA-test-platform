#!/usr/bin/env python3
"""Direct UART command sender for the FPGA eDRAM platform."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

import uart_host_protocol as proto
import uart_serial_transport as uart_io


CommandError = uart_io.UartTransportError
PATTERN_CHOICES = ("doc", "walking", "checker", "inverse-checker", "increment", "zero", "ones")


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def parse_byte_sequence(text: str, *, empty_ok: bool = False) -> tuple[int, ...]:
    normalized = text.replace(",", " ").replace(":", " ").replace(";", " ")
    parts = [part for part in normalized.split() if part]
    if not parts:
        if empty_ok:
            return ()
        raise ValueError("byte sequence is empty")

    expanded: list[str] = []
    for part in parts:
        token = part[2:] if part.lower().startswith("0x") else part
        if (
            len(token) > 2 and
            len(token) % 2 == 0 and
            all(char in "0123456789abcdefABCDEF" for char in token)
        ):
            expanded.extend(token[index : index + 2] for index in range(0, len(token), 2))
        else:
            expanded.append(part)

    values: list[int] = []
    for part in expanded:
        try:
            value = int(part[2:], 16) if part.lower().startswith("0x") else int(part, 16)
        except ValueError:
            raise ValueError(f"invalid byte value: {part}") from None
        if not 0 <= value <= 0xFF:
            raise ValueError(f"byte value out of range: {part}")
        values.append(value)
    return tuple(values)


def validate_byte(value: int, name: str) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer byte") from exc
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} out of range: {value} (expected 0..255)")
    return value


def pattern_bytes(row: int, pattern: str) -> tuple[int, ...]:
    row = proto.validate_row(row)
    if pattern == "doc":
        return (0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77)
    if pattern == "walking":
        return tuple(1 << index for index in range(proto.EDRAM_ROW_BYTES))
    if pattern == "checker":
        return tuple(0xAA if index % 2 == 0 else 0x55 for index in range(proto.EDRAM_ROW_BYTES))
    if pattern == "inverse-checker":
        return tuple(0x55 if index % 2 == 0 else 0xAA for index in range(proto.EDRAM_ROW_BYTES))
    if pattern == "increment":
        return tuple((row + index) & 0xFF for index in range(proto.EDRAM_ROW_BYTES))
    if pattern == "zero":
        return tuple(0x00 for _ in range(proto.EDRAM_ROW_BYTES))
    if pattern == "ones":
        return tuple(0xFF for _ in range(proto.EDRAM_ROW_BYTES))
    raise ValueError(f"unknown pattern: {pattern}")


def row_data_from_args(row: int, args) -> tuple[int, ...]:
    if args.data is not None:
        data = parse_byte_sequence(args.data)
        if len(data) != proto.EDRAM_ROW_BYTES:
            raise ValueError(f"--data needs exactly {proto.EDRAM_ROW_BYTES} byte(s), got {len(data)}")
        return data
    return pattern_bytes(row, args.pattern)


def decode_status_payload(data: Sequence[int]) -> dict[str, int | str]:
    if len(data) != 2:
        raise CommandError(
            f"STATUS: payload length mismatch, expected 2, got {len(data)} "
            f"({proto.format_bytes(data)})"
        )
    state, last_err = data
    return {
        "busy": state & 0x01,
        "state": state,
        "reserved": state & 0xFE,
        "last_err": last_err,
        "last_err_name": proto.status_name(last_err),
    }


def snapshot_fields(snapshot: proto.OutputSnapshot) -> dict[str, int | str | list[int]]:
    return {
        "load_n": snapshot.load_n,
        "read_n": snapshot.read_n,
        "en_wwl_n": snapshot.en_wwl_n,
        "en_rwl_n": snapshot.en_rwl_n,
        "wg": snapshot.wg,
        "rg": snapshot.rg,
        "din": snapshot.din,
        "a": snapshot.a,
        "w": snapshot.w,
        "snapshot_raw": list(snapshot.raw),
        "snapshot_raw_hex": proto.format_bytes(snapshot.raw),
    }


def response_json(
    response: proto.Response,
    tx_frame: bytes,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": response.ok,
        "status": response.status,
        "status_name": response.status_name,
        "op": response.op,
        "op_name": response.op_name,
        "data": list(response.data),
        "data_hex": proto.format_bytes(response.data),
        "raw_tx": list(tx_frame),
        "raw_tx_hex": proto.format_bytes(tx_frame),
        "raw_rx": list(response.raw),
        "raw_rx_hex": proto.format_bytes(response.raw),
    }
    if extra:
        result.update(extra)
    return result


def emit_result(
    args,
    response: proto.Response,
    tx_frame: bytes,
    text: str,
    extra: dict[str, Any] | None = None,
) -> None:
    if args.json:
        print(json.dumps(response_json(response, tx_frame, extra), sort_keys=True))
        return
    print(text)


def command_exchange(
    args,
    op: int,
    frame: bytes,
    *,
    expected_data: Sequence[int] | None = None,
    expected_data_len: int | None = None,
    allow_nack: bool = False,
) -> proto.Response:
    config = uart_io.config_from_args(args)
    port = uart_io.open_serial(config)
    try:
        return uart_io.exchange(
            port,
            op,
            frame,
            timeout=config.timeout,
            verbose=args.verbose and not args.json,
            expected_data=expected_data,
            expected_data_len=expected_data_len,
            allow_nack=allow_nack,
        )
    finally:
        port.close()


def run_list(args) -> int:
    ports = uart_io.list_serial_ports()
    if args.json:
        data = [
            {
                "device": port.device,
                "description": port.description or "",
                "hwid": port.hwid or "",
            }
            for port in ports
        ]
        print(json.dumps({"ports": data}, sort_keys=True))
        return 0

    if not ports:
        print("No serial ports found.")
        return 0
    for port in ports:
        description = port.description or ""
        hwid = port.hwid or ""
        print(f"{port.device}\t{description}\t{hwid}")
    return 0


def run_ping(args) -> int:
    frame = proto.ping_frame()
    response = command_exchange(
        args,
        proto.OP_PING,
        frame,
        expected_data=(proto.PING_RESP_DATA,),
    )
    emit_result(
        args,
        response,
        frame,
        f"PING ACK payload={proto.format_bytes(response.data)}",
        {"payload": list(response.data), "payload_hex": proto.format_bytes(response.data)},
    )
    return 0


def run_reset(args) -> int:
    frame = proto.reset_frame()
    response = command_exchange(args, proto.OP_RESET, frame, expected_data=())
    emit_result(args, response, frame, "RESET ACK")
    return 0


def run_status(args) -> int:
    frame = proto.status_frame()
    response = command_exchange(
        args,
        proto.OP_STATUS,
        frame,
        expected_data_len=2,
    )
    decoded = decode_status_payload(response.data)
    text = (
        "STATUS ACK "
        f"busy={decoded['busy']} state=0x{decoded['state']:02X} "
        f"reserved=0x{decoded['reserved']:02X} "
        f"last_err={decoded['last_err_name']}(0x{decoded['last_err']:02X})"
    )
    emit_result(args, response, frame, text, decoded)
    return 0


def run_write_row(args) -> int:
    row = proto.validate_row(args.row)
    data = row_data_from_args(row, args)
    frame = proto.write_row_frame(row, data)
    response = command_exchange(args, proto.OP_WRITE_ROW, frame, expected_data=())
    text = f"WRITE_ROW ACK row={row} data={proto.format_bytes(data)}"
    emit_result(
        args,
        response,
        frame,
        text,
        {"row": row, "written_data": list(data), "written_data_hex": proto.format_bytes(data)},
    )
    return 0


def run_read_group(args) -> int:
    row = proto.validate_row(args.row)
    group = proto.validate_group(args.group)
    frame = proto.read_group_frame(row, group)
    response = command_exchange(
        args,
        proto.OP_READ_GROUP,
        frame,
        expected_data_len=1,
    )
    value = response.data[0]
    text = f"READ_GROUP ACK row={row} group={group} data={value:02X}"
    emit_result(args, response, frame, text, {"row": row, "group": group, "value": value})
    return 0


def run_read_row(args) -> int:
    row = proto.validate_row(args.row)
    frame = proto.read_row_frame(row)
    response = command_exchange(
        args,
        proto.OP_READ_ROW,
        frame,
        expected_data_len=proto.EDRAM_ROW_BYTES,
    )
    text = f"READ_ROW ACK row={row} data={proto.format_bytes(response.data)}"
    emit_result(
        args,
        response,
        frame,
        text,
        {"row": row, "row_data": list(response.data), "row_data_hex": proto.format_bytes(response.data)},
    )
    return 0


def run_outputs(args) -> int:
    frame = proto.read_outputs_frame()
    response = command_exchange(
        args,
        proto.OP_READ_OUTPUTS,
        frame,
        expected_data_len=proto.EDRAM_OUTPUT_SNAPSHOT_BYTES,
    )
    snapshot = proto.decode_output_snapshot(response.data)
    text = f"OUTPUTS ACK {snapshot.summary()} raw={proto.format_bytes(snapshot.raw)}"
    emit_result(args, response, frame, text, snapshot_fields(snapshot))
    return 0


def run_trace(args) -> int:
    index = validate_byte(args.index, "--index")
    frame = proto.read_output_trace_frame(index)
    response = command_exchange(
        args,
        proto.OP_READ_OUTPUT_TRACE,
        frame,
        expected_data_len=proto.EDRAM_OUTPUT_TRACE_RESP_BYTES,
    )
    count, returned_index, snapshot = proto.decode_output_trace_payload(response.data)
    if returned_index != index:
        raise CommandError(f"TRACE: returned index {returned_index}, expected {index}")
    fields = {"count": count, "index": returned_index}
    fields.update(snapshot_fields(snapshot))
    text = (
        f"TRACE ACK count={count} index={returned_index} "
        f"{snapshot.summary()} raw={proto.format_bytes(snapshot.raw)}"
    )
    emit_result(args, response, frame, text, fields)
    return 0


def run_raw(args) -> int:
    op = validate_byte(args.op, "--op")
    raw_args = parse_byte_sequence(" ".join(args.args), empty_ok=True)
    frame = proto.build_request(op, raw_args)
    response = command_exchange(args, op, frame, allow_nack=args.allow_nack)
    payload = proto.format_bytes(response.data) if response.data else "<empty>"
    text = (
        f"RAW {response.status_name} op={response.op_name}(0x{response.op:02X}) "
        f"payload={payload}"
    )
    emit_result(
        args,
        response,
        frame,
        text,
        {
            "request_op": op,
            "request_op_name": proto.op_name(op),
            "request_args": list(raw_args),
            "request_args_hex": proto.format_bytes(raw_args),
        },
    )
    return 0


def add_serial_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", required=True, help="Serial port, for example COM7 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=parse_int, default=proto.DEFAULT_BAUD, help="UART baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Per-command timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Print raw TX/RX frames in human output mode")
    parser.add_argument("--json", action="store_true", help="Print one JSON object instead of human text")
    parser.add_argument("--no-drain", dest="drain", action="store_false", help="Do not drain serial buffers on open")
    parser.set_defaults(drain=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send individual FPGA eDRAM UART protocol commands."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available serial ports")
    list_parser.add_argument("--json", action="store_true", help="Print serial ports as JSON")
    list_parser.set_defaults(func=run_list)

    ping_parser = subparsers.add_parser("ping", help="Send PING")
    add_serial_args(ping_parser)
    ping_parser.set_defaults(func=run_ping)

    reset_parser = subparsers.add_parser("reset", help="Send RESET")
    add_serial_args(reset_parser)
    reset_parser.set_defaults(func=run_reset)

    status_parser = subparsers.add_parser("status", help="Send STATUS")
    add_serial_args(status_parser)
    status_parser.set_defaults(func=run_status)

    write_parser = subparsers.add_parser("write-row", help="Send WRITE_ROW")
    add_serial_args(write_parser)
    write_parser.add_argument("--row", type=parse_int, required=True, help="eDRAM row, 0..63")
    data_group = write_parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument(
        "--data",
        help="Explicit 8-byte row data, e.g. '00 11 22 33 44 55 66 77' or 0011223344556677",
    )
    data_group.add_argument("--pattern", choices=PATTERN_CHOICES, help="Generated 8-byte row data")
    write_parser.set_defaults(func=run_write_row)

    read_group_parser = subparsers.add_parser("read-group", help="Send READ_GROUP")
    add_serial_args(read_group_parser)
    read_group_parser.add_argument("--row", type=parse_int, required=True, help="eDRAM row, 0..63")
    read_group_parser.add_argument("--group", type=parse_int, required=True, help="eDRAM group, 0..7")
    read_group_parser.set_defaults(func=run_read_group)

    read_row_parser = subparsers.add_parser("read-row", help="Send READ_ROW")
    add_serial_args(read_row_parser)
    read_row_parser.add_argument("--row", type=parse_int, required=True, help="eDRAM row, 0..63")
    read_row_parser.set_defaults(func=run_read_row)

    outputs_parser = subparsers.add_parser("outputs", help="Send READ_OUTPUTS")
    add_serial_args(outputs_parser)
    outputs_parser.set_defaults(func=run_outputs)

    trace_parser = subparsers.add_parser("trace", help="Send READ_OUTPUT_TRACE")
    add_serial_args(trace_parser)
    trace_parser.add_argument("--index", type=parse_int, required=True, help="Trace record index, 0..255")
    trace_parser.set_defaults(func=run_trace)

    raw_parser = subparsers.add_parser("raw", help="Send a framed request with custom opcode/args")
    add_serial_args(raw_parser)
    raw_parser.add_argument("--op", type=parse_int, required=True, help="Opcode byte, for example 0x05")
    raw_parser.add_argument(
        "--args",
        nargs="*",
        default=(),
        help="Optional argument bytes, e.g. --args 00 11 or --args 0011",
    )
    raw_parser.add_argument(
        "--allow-nack",
        action="store_true",
        help="Treat FPGA NACK responses as a displayed diagnostic result",
    )
    raw_parser.set_defaults(func=run_raw)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (CommandError, proto.UartProtocolError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
