#!/usr/bin/env python3
"""Host-side UART tests for the FPGA eDRAM platform."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Sequence

import uart_host_protocol as proto
import uart_serial_transport as uart_io


HostTestError = uart_io.UartTransportError
SerialTimeoutError = uart_io.SerialTimeoutError


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def parse_byte_sequence(text: str) -> tuple[int, ...]:
    normalized = text.replace(",", " ").replace(":", " ").replace(";", " ")
    parts = [part for part in normalized.split() if part]
    if len(parts) == 1:
        token = parts[0]
        if token.lower().startswith("0x"):
            token = token[2:]
        if token and len(token) % 2 == 0 and all(char in "0123456789abcdefABCDEF" for char in token):
            parts = [token[index : index + 2] for index in range(0, len(token), 2)]

    if not parts:
        raise ValueError("byte pattern is empty")

    values: list[int] = []
    for part in parts:
        try:
            value = int(part[2:], 16) if part.lower().startswith("0x") else int(part, 16)
        except ValueError:
            raise ValueError(f"invalid byte value: {part}") from None
        if not 0 <= value <= 0xFF:
            raise ValueError(f"byte value out of range: {part}")
        values.append(value)
    return tuple(values)


def pattern_bytes(row: int, pattern: str, data_text: str | None) -> tuple[int, ...]:
    row = proto.validate_row(row)
    if data_text:
        values = parse_byte_sequence(data_text)
        if len(values) != proto.EDRAM_ROW_BYTES:
            raise HostTestError(
                f"--data needs exactly {proto.EDRAM_ROW_BYTES} byte(s), got {len(values)}"
            )
        return values

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
    raise HostTestError(f"unknown pattern: {pattern}")


def open_serial(args):
    return uart_io.open_serial(uart_io.config_from_args(args))


def exchange(
    port,
    op: int,
    frame: bytes,
    args,
    *,
    expected_data: Sequence[int] | None = None,
    expected_data_len: int | None = None,
) -> proto.Response:
    return uart_io.exchange(
        port,
        op,
        frame,
        timeout=args.timeout,
        verbose=args.verbose,
        expected_data=expected_data,
        expected_data_len=expected_data_len,
    )


def decode_status_payload(data: Sequence[int]) -> str:
    if len(data) != 2:
        raise HostTestError(
            f"STATUS: payload length mismatch, expected 2, got {len(data)} ({proto.format_bytes(data)})"
        )
    state, last_err = data
    busy = state & 0x01
    reserved = state & 0xFE
    return (
        f"busy={busy} state=0x{state:02X} reserved=0x{reserved:02X} "
        f"last_err={proto.status_name(last_err)}(0x{last_err:02X})"
    )


def format_snapshot(snapshot: proto.OutputSnapshot) -> str:
    return f"{snapshot.summary()} raw={proto.format_bytes(snapshot.raw)}"


def run_basic_sequence(port, args, final_label: str = "BASIC") -> proto.Response:
    print(f"Running {final_label.lower()} UART test on {args.port} at {args.baud} baud")
    exchange(port, proto.OP_RESET, proto.reset_frame(), args, expected_data=())
    print("RESET: PASS")

    exchange(
        port,
        proto.OP_PING,
        proto.ping_frame(),
        args,
        expected_data=(proto.PING_RESP_DATA,),
    )
    print(f"PING: PASS payload={proto.PING_RESP_DATA:02X}")

    status = exchange(
        port,
        proto.OP_STATUS,
        proto.status_frame(),
        args,
        expected_data_len=2,
    )
    print(f"STATUS: PASS {decode_status_payload(status.data)}")
    print(f"{final_label}: PASS")
    return status


def run_basic(args) -> int:
    port = open_serial(args)
    try:
        run_basic_sequence(port, args, "BASIC")
    finally:
        port.close()
    return 0


def run_ping(args) -> int:
    if args.count <= 0:
        raise HostTestError("--count must be greater than 0")

    port = open_serial(args)
    try:
        for index in range(args.count):
            exchange(
                port,
                proto.OP_PING,
                proto.ping_frame(),
                args,
                expected_data=(proto.PING_RESP_DATA,),
            )
            print(f"PING {index + 1}/{args.count}: PASS payload={proto.PING_RESP_DATA:02X}")
            if args.delay and index + 1 < args.count:
                time.sleep(args.delay)
    finally:
        port.close()
    return 0


def run_status(args) -> int:
    port = open_serial(args)
    try:
        status = exchange(
            port,
            proto.OP_STATUS,
            proto.status_frame(),
            args,
            expected_data_len=2,
        )
        print(f"STATUS: PASS {decode_status_payload(status.data)}")
    finally:
        port.close()
    return 0


def run_outputs(args) -> int:
    port = open_serial(args)
    try:
        response = exchange(
            port,
            proto.OP_READ_OUTPUTS,
            proto.read_outputs_frame(),
            args,
            expected_data_len=proto.EDRAM_OUTPUT_SNAPSHOT_BYTES,
        )
        snapshot = proto.decode_output_snapshot(response.data)
        print(f"OUTPUTS: PASS {format_snapshot(snapshot)}")
    finally:
        port.close()
    return 0


def read_output_trace_record(port, args, index: int) -> tuple[int, int, proto.OutputSnapshot]:
    response = exchange(
        port,
        proto.OP_READ_OUTPUT_TRACE,
        proto.read_output_trace_frame(index),
        args,
        expected_data_len=proto.EDRAM_OUTPUT_TRACE_RESP_BYTES,
    )
    count, returned_index, snapshot = proto.decode_output_trace_payload(response.data)
    if returned_index != index:
        raise HostTestError(
            f"READ_OUTPUT_TRACE: returned index {returned_index}, expected {index}"
        )
    return count, returned_index, snapshot


def collect_output_trace(port, args) -> list[proto.OutputSnapshot]:
    count, _, first_snapshot = read_output_trace_record(port, args, 0)
    if count <= 0:
        raise HostTestError("READ_OUTPUT_TRACE: FPGA reported zero trace records")
    if count > 64:
        raise HostTestError(f"READ_OUTPUT_TRACE: unreasonable trace count {count}")

    records = [first_snapshot]
    for index in range(1, count):
        next_count, _, snapshot = read_output_trace_record(port, args, index)
        if next_count != count:
            raise HostTestError(
                f"READ_OUTPUT_TRACE: count changed from {count} to {next_count}"
            )
        records.append(snapshot)
    return records


def require_ordered_snapshot(
    records: Sequence[proto.OutputSnapshot],
    start_index: int,
    label: str,
    predicate,
) -> int:
    for index in range(start_index, len(records)):
        if predicate(records[index]):
            return index + 1
    raise HostTestError(f"WRITE_SELFCHECK: missing trace record for {label}")


def verify_write_trace(
    records: Sequence[proto.OutputSnapshot],
    row: int,
    data: Sequence[int],
) -> None:
    search_start = 0
    for group, expected in enumerate(data):
        search_start = require_ordered_snapshot(
            records,
            search_start,
            f"group {group} DIN=0x{expected:02X}",
            lambda snapshot, group=group, expected=expected: (
                snapshot.load_n == 0 and
                snapshot.read_n == 1 and
                snapshot.en_wwl_n == 1 and
                snapshot.en_rwl_n == 1 and
                snapshot.wg == group and
                snapshot.din == expected
            ),
        )

    require_ordered_snapshot(
        records,
        search_start,
        f"row-write A={row}",
        lambda snapshot: (
            snapshot.load_n == 1 and
            snapshot.read_n == 1 and
            snapshot.en_wwl_n == 0 and
            snapshot.en_rwl_n == 1 and
            snapshot.a == row
        ),
    )


def run_write_selfcheck(args) -> int:
    row = proto.validate_row(args.row)
    data = pattern_bytes(row, args.pattern, args.data)

    port = open_serial(args)
    try:
        print(
            f"WRITE_SELFCHECK: row={row} pattern={args.pattern} "
            f"data={proto.format_bytes(data)}"
        )
        exchange(port, proto.OP_RESET, proto.reset_frame(), args, expected_data=())
        print("RESET: PASS")

        exchange(port, proto.OP_WRITE_ROW, proto.write_row_frame(row, data), args, expected_data=())
        print("WRITE_ROW: PASS")

        records = collect_output_trace(port, args)
        if args.verbose:
            for index, snapshot in enumerate(records):
                print(f"TRACE {index}: {format_snapshot(snapshot)}")

        verify_write_trace(records, row, data)
        print(f"WRITE_SELFCHECK: PASS trace_records={len(records)}")
    finally:
        port.close()
    return 0


def run_full(args) -> int:
    row = proto.validate_row(args.row)
    data = pattern_bytes(row, args.pattern, args.data)

    port = open_serial(args)
    try:
        run_basic_sequence(port, args, "BASIC")

        print(
            f"WRITE_ROW: row={row} pattern={args.pattern} data={proto.format_bytes(data)}"
        )
        exchange(port, proto.OP_WRITE_ROW, proto.write_row_frame(row, data), args, expected_data=())
        print("WRITE_ROW: PASS")

        for group, expected in enumerate(data):
            response = exchange(
                port,
                proto.OP_READ_GROUP,
                proto.read_group_frame(row, group),
                args,
                expected_data_len=1,
            )
            actual = response.data[0]
            if actual != expected:
                raise HostTestError(
                    f"READ_GROUP mismatch: row={row} group={group} "
                    f"expected=0x{expected:02X} actual=0x{actual:02X}"
                )
        print("READ_GROUP: PASS groups=0..7")

        response = exchange(
            port,
            proto.OP_READ_ROW,
            proto.read_row_frame(row),
            args,
            expected_data_len=proto.EDRAM_ROW_BYTES,
        )
        for group, (expected, actual) in enumerate(zip(data, response.data)):
            if actual != expected:
                raise HostTestError(
                    f"READ_ROW mismatch: row={row} group={group} "
                    f"expected=0x{expected:02X} actual=0x{actual:02X}"
                )
        print(f"READ_ROW: PASS data={proto.format_bytes(response.data)}")

        status = exchange(
            port,
            proto.OP_STATUS,
            proto.status_frame(),
            args,
            expected_data_len=2,
        )
        print(f"STATUS final: PASS {decode_status_payload(status.data)}")
        print("FULL: PASS")
    finally:
        port.close()
    return 0


def run_list(args) -> int:
    ports = uart_io.list_serial_ports()
    if not ports:
        print("No serial ports found.")
        return 0

    for port in ports:
        description = port.description or ""
        hwid = port.hwid or ""
        print(f"{port.device}\t{description}\t{hwid}")
    return 0


def add_serial_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", required=True, help="Serial port, for example COM7 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=parse_int, default=proto.DEFAULT_BAUD, help="UART baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Per-command timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Print raw TX/RX frames")
    parser.add_argument("--no-drain", dest="drain", action="store_false", help="Do not drain serial buffers on open")
    parser.set_defaults(drain=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Host UART tests for the FPGA eDRAM platform."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available serial ports")
    list_parser.set_defaults(func=run_list)

    for name in ("basic", "smoke"):
        mode_parser = subparsers.add_parser(
            name,
            help="Run RESET, PING, and STATUS without touching eDRAM contents",
        )
        add_serial_args(mode_parser)
        mode_parser.set_defaults(func=run_basic)

    ping_parser = subparsers.add_parser("ping", help="Run one or more PING transactions")
    add_serial_args(ping_parser)
    ping_parser.add_argument("--count", type=parse_int, default=1, help="Number of PING requests")
    ping_parser.add_argument("--delay", type=float, default=0.0, help="Delay between PING requests")
    ping_parser.set_defaults(func=run_ping)

    status_parser = subparsers.add_parser("status", help="Run a STATUS transaction")
    add_serial_args(status_parser)
    status_parser.set_defaults(func=run_status)

    outputs_parser = subparsers.add_parser(
        "outputs",
        help="Read the live eDRAM output-port snapshot over UART",
    )
    add_serial_args(outputs_parser)
    outputs_parser.set_defaults(func=run_outputs)

    write_selfcheck_parser = subparsers.add_parser(
        "write-selfcheck",
        help="Write a row and verify FPGA output-port trace records against the requested pattern",
    )
    add_serial_args(write_selfcheck_parser)
    write_selfcheck_parser.add_argument(
        "--row",
        type=parse_int,
        required=True,
        help="Scratch eDRAM row to overwrite, 0..63",
    )
    write_selfcheck_parser.add_argument(
        "--pattern",
        choices=("doc", "walking", "checker", "inverse-checker", "increment", "zero", "ones"),
        default="doc",
        help="Generated 8-byte write pattern",
    )
    write_selfcheck_parser.add_argument(
        "--data",
        help="Explicit 8-byte pattern, e.g. '00 11 22 33 44 55 66 77' or 0011223344556677",
    )
    write_selfcheck_parser.set_defaults(func=run_write_selfcheck)

    for name in ("full", "memtest"):
        mode_parser = subparsers.add_parser(
            name,
            help="Run all UART ISA commands through the eDRAM transaction path",
        )
        add_serial_args(mode_parser)
        mode_parser.add_argument(
            "--row",
            type=parse_int,
            required=True,
            help="Scratch eDRAM row to overwrite, 0..63",
        )
        mode_parser.add_argument(
            "--pattern",
            choices=("doc", "walking", "checker", "inverse-checker", "increment", "zero", "ones"),
            default="doc",
            help="Generated 8-byte write pattern",
        )
        mode_parser.add_argument(
            "--data",
            help="Explicit 8-byte pattern, e.g. '00 11 22 33 44 55 66 77' or 0011223344556677",
        )
        mode_parser.set_defaults(func=run_full)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (HostTestError, proto.UartProtocolError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
