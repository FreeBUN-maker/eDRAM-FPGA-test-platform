#!/usr/bin/env python3
"""Check RTL module inputs for Vivado-friendly explicit net types."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


NET_TYPES = {
    "wire",
    "tri",
    "tri0",
    "tri1",
    "triand",
    "trior",
    "trireg",
    "uwire",
    "wand",
    "wor",
    "supply0",
    "supply1",
    "var",
}

MODULE_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b")
INPUT_RE = re.compile(r"^\s*input\b(?P<rest>.*)")


def strip_comments(text: str) -> str:
    result: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("//", i):
            newline = text.find("\n", i)
            if newline < 0:
                break
            result.append("\n")
            i = newline + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            comment = text[i + 2 :] if end < 0 else text[i + 2 : end]
            result.append("\n" * comment.count("\n"))
            i = len(text) if end < 0 else end + 2
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def find_matching_paren(text: str, open_index: int) -> int:
    depth = 0
    for index in range(open_index, len(text)):
        char = text[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return -1


def skip_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def module_port_lists(text: str):
    for match in MODULE_RE.finditer(text):
        module_name = match.group(1)
        index = skip_space(text, match.end())

        if index < len(text) and text[index] == "#":
            index = skip_space(text, index + 1)
            if index >= len(text) or text[index] != "(":
                continue
            param_close = find_matching_paren(text, index)
            if param_close < 0:
                continue
            index = skip_space(text, param_close + 1)

        if index >= len(text) or text[index] != "(":
            continue

        port_close = find_matching_paren(text, index)
        if port_close < 0:
            continue

        start_line = text.count("\n", 0, index) + 1
        yield module_name, start_line, text[index + 1 : port_close]


def missing_input_net_type(line: str) -> bool:
    match = INPUT_RE.match(line)
    if not match:
        return False

    rest = match.group("rest").strip()
    if not rest:
        return True

    first_token = rest.split(None, 1)[0].rstrip(",")
    return first_token not in NET_TYPES


def check_file(path: Path) -> list[str]:
    text = strip_comments(path.read_text(encoding="utf-8"))
    findings: list[str] = []

    for module_name, start_line, ports in module_port_lists(text):
        for offset, line in enumerate(ports.splitlines(), start=1):
            if missing_input_net_type(line):
                findings.append(
                    f"{path}:{start_line + offset}: module {module_name} "
                    f"input port missing explicit net type: {line.strip()}"
                )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, default=sorted(Path("src/rtl").glob("*.sv")))
    args = parser.parse_args()

    findings: list[str] = []
    for path in args.paths:
        findings.extend(check_file(path))

    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1

    print(f"Checked {len(args.paths)} SystemVerilog file(s); module input net types are explicit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
