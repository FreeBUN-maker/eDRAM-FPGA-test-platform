#!/usr/bin/env python3
"""Shared serial transport helpers for the FPGA eDRAM UART protocol."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Sequence

import uart_host_protocol as proto


INSTALL_HINT = (
    "pyserial is required for hardware UART tests. "
    "Install it with: python -m pip install pyserial"
)
MAX_RESPONSE_BODY_LEN = 0xFF


class UartTransportError(RuntimeError):
    """Raised for user-facing UART serial transport failures."""


class SerialTimeoutError(UartTransportError):
    """Raised when a serial read times out."""


@dataclass(frozen=True)
class SerialConfig:
    port: str
    baud: int = proto.DEFAULT_BAUD
    timeout: float = 1.0
    drain: bool = True


def config_from_args(args) -> SerialConfig:
    return SerialConfig(
        port=args.port,
        baud=args.baud,
        timeout=args.timeout,
        drain=getattr(args, "drain", True),
    )


def require_serial():
    try:
        import serial  # type: ignore
    except ModuleNotFoundError as exc:
        if exc.name == "serial":
            raise UartTransportError(INSTALL_HINT) from exc
        raise
    return serial


def require_list_ports():
    require_serial()
    try:
        from serial.tools import list_ports  # type: ignore
    except ModuleNotFoundError as exc:
        raise UartTransportError(INSTALL_HINT) from exc
    return list_ports


def list_serial_ports():
    list_ports = require_list_ports()
    return sorted(list_ports.comports(), key=lambda item: item.device)


def validate_config(config: SerialConfig) -> None:
    if not config.port:
        raise UartTransportError("--port is required")
    if config.baud <= 0:
        raise UartTransportError("--baud must be greater than 0")
    if config.timeout <= 0:
        raise UartTransportError("--timeout must be greater than 0")


def open_serial(config: SerialConfig):
    validate_config(config)
    serial = require_serial()
    try:
        port = serial.Serial(
            port=config.port,
            baudrate=config.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=config.timeout,
            write_timeout=config.timeout,
        )
    except Exception as exc:
        raise UartTransportError(f"failed to open serial port {config.port!r}: {exc}") from exc

    if config.drain:
        try:
            port.reset_input_buffer()
            port.reset_output_buffer()
        except Exception as exc:
            port.close()
            raise UartTransportError(
                f"failed to drain serial port {config.port!r}: {exc}"
            ) from exc
    return port


def read_exact(port, count: int, deadline: float, context: str) -> bytes:
    data = bytearray()
    while len(data) < count:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SerialTimeoutError(
                f"{context}: timed out while reading {count} byte(s), got {len(data)}"
            )
        port.timeout = remaining
        try:
            chunk = port.read(count - len(data))
        except Exception as exc:
            raise UartTransportError(f"{context}: serial read failed: {exc}") from exc
        if not chunk:
            raise SerialTimeoutError(
                f"{context}: timed out while reading {count} byte(s), got {len(data)}"
            )
        data.extend(chunk)
    return bytes(data)


def read_response(
    port,
    command_name: str,
    timeout: float,
    verbose: bool = False,
    *,
    max_response_body_len: int = MAX_RESPONSE_BODY_LEN,
) -> proto.Response:
    deadline = time.monotonic() + timeout
    dropped = bytearray()

    while True:
        byte = read_exact(port, 1, deadline, f"{command_name} response SOF")
        if byte[0] == proto.SOF_RESP:
            break
        dropped.extend(byte)

    length = read_exact(port, 1, deadline, f"{command_name} response length")[0]
    if length > max_response_body_len:
        raise UartTransportError(
            f"{command_name}: response LEN={length} exceeds protocol maximum "
            f"{max_response_body_len}"
        )

    rest = read_exact(port, length + 1, deadline, f"{command_name} response body/checksum")
    frame = bytes([proto.SOF_RESP, length]) + rest

    if verbose and dropped:
        print(f"{command_name}: dropped before SOF_R: {proto.format_bytes(dropped)}")

    try:
        return proto.parse_response(frame)
    except proto.UartProtocolError as exc:
        raise UartTransportError(
            f"{command_name}: malformed response {proto.format_bytes(frame)}: {exc}"
        ) from exc


def write_frame(port, command_name: str, frame: bytes) -> None:
    try:
        written = port.write(frame)
        port.flush()
    except Exception as exc:
        raise UartTransportError(f"{command_name}: serial write failed: {exc}") from exc

    if written is None:
        written = len(frame)
    if written != len(frame):
        raise UartTransportError(
            f"{command_name}: wrote {written} byte(s), expected {len(frame)}"
        )


def exchange(
    port,
    op: int,
    frame: bytes,
    *,
    timeout: float,
    verbose: bool = False,
    expected_data: Sequence[int] | None = None,
    expected_data_len: int | None = None,
    allow_nack: bool = False,
    check_op_echo: bool = True,
    command_name: str | None = None,
    max_response_body_len: int = MAX_RESPONSE_BODY_LEN,
) -> proto.Response:
    name = command_name or proto.op_name(op)
    if verbose:
        print(f"TX {name}: {proto.format_bytes(frame)}")

    write_frame(port, name, frame)
    response = read_response(
        port,
        name,
        timeout,
        verbose,
        max_response_body_len=max_response_body_len,
    )

    if verbose:
        print(f"RX {name}: {proto.format_bytes(response.raw)}")

    if check_op_echo and response.op != op:
        raise UartTransportError(
            f"{name}: unexpected OP_ECHO {response.op_name} "
            f"(0x{response.op:02X}), expected {name}"
        )

    if response.status != proto.STAT_ACK:
        if allow_nack:
            return response
        payload = proto.format_bytes(response.data) if response.data else "<empty>"
        raise UartTransportError(f"{name}: FPGA returned {response.status_name}, payload={payload}")

    if expected_data_len is not None and len(response.data) != expected_data_len:
        raise UartTransportError(
            f"{name}: payload length mismatch, expected {expected_data_len}, "
            f"got {len(response.data)} ({proto.format_bytes(response.data)})"
        )

    if expected_data is not None and tuple(response.data) != tuple(expected_data):
        raise UartTransportError(
            f"{name}: payload mismatch, expected {proto.format_bytes(expected_data)}, "
            f"got {proto.format_bytes(response.data)}"
        )

    return response
