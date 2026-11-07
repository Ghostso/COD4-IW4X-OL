#!/usr/bin/env python3
"""Restore CODOL playlist text damaged by a GBK/Windows-1252 conversion."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


LOCALIZED_LINE = re.compile(
    r"^(?P<prefix>\s*)(?P<kind>name|description)(?P<separator>\s+)"
    r"(?P<language>chinese|english)(?P<value_separator>\s+)"
    r"(?P<value>.*?)(?P<newline>\r?\n)?$"
)


@dataclass(frozen=True)
class RestoreStats:
    localized_pairs: int
    chinese_characters: int


def repair_text(text: str) -> str:
    try:
        source_bytes = text.encode("windows-1252", errors="strict")
        repaired = source_bytes.decode("gbk", errors="strict")
    except UnicodeError as error:
        raise ValueError(
            "input is not a strictly reversible Windows-1252 rendering of GBK text"
        ) from error

    try:
        round_trip = repaired.encode("gbk").decode("windows-1252")
    except UnicodeError as error:
        raise ValueError("restored text failed the reverse conversion check") from error
    if round_trip != text:
        raise ValueError("restored text does not reproduce the original input")
    return repaired


def format_localized_line(match: re.Match[str], value: str) -> str:
    return (
        f"{match.group('prefix')}{match.group('kind')}"
        f"{match.group('separator')}{match.group('language')}"
        f"{match.group('value_separator')}{value}"
        f"{match.group('newline') or ''}"
    )


def restore_localized_fields(text: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    pairs = 0
    index = 0
    while index < len(lines):
        first = LOCALIZED_LINE.match(lines[index])
        if not first:
            index += 1
            continue
        if first.group("language") != "chinese":
            raise ValueError(f"unexpected unpaired English field at line {index + 1}")
        if index + 1 >= len(lines):
            raise ValueError(f"missing English field after line {index + 1}")

        second = LOCALIZED_LINE.match(lines[index + 1])
        if (
            not second
            or second.group("language") != "english"
            or second.group("kind") != first.group("kind")
        ):
            raise ValueError(f"missing matching English field after line {index + 1}")

        chinese_value = second.group("value")
        english_value = first.group("value")
        lines[index] = format_localized_line(first, chinese_value)
        lines[index + 1] = format_localized_line(second, english_value)
        pairs += 1
        index += 2

    return "".join(lines), pairs


def restore_document(
    source: bytes, output_encoding: str = "gbk"
) -> tuple[bytes, RestoreStats]:
    if source.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is not expected in this playlist format")
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("input is not valid UTF-8") from error

    repaired = repair_text(text)
    repaired, pair_count = restore_localized_fields(repaired)
    chinese_count = sum("\u4e00" <= character <= "\u9fff" for character in repaired)
    if pair_count == 0 or chinese_count == 0:
        raise ValueError("input contained no recoverable localized playlist fields")
    try:
        output = repaired.encode(output_encoding, errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"restored text cannot be encoded as {output_encoding}") from error
    return output, RestoreStats(pair_count, chinese_count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Restore a CODOL playlist whose GBK Chinese text was decoded as "
            "Windows-1252 and whose Chinese/English values were swapped."
        )
    )
    parser.add_argument("input", type=Path, help="damaged UTF-8 playlist")
    parser.add_argument("output", type=Path, help="restored playlist")
    parser.add_argument(
        "--output-encoding",
        choices=("gbk", "utf-8"),
        default="gbk",
        help="output encoding (default: gbk, as expected by the CODOL client)",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="allow replacing an existing output file"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"input file does not exist: {args.input}")
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"output already exists (use --overwrite): {args.output}")

    try:
        output, stats = restore_document(args.input.read_bytes(), args.output_encoding)
    except ValueError as error:
        raise SystemExit(f"restore failed: {error}") from error

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(
        f"restored {stats.localized_pairs} localized pairs and "
        f"{stats.chinese_characters} Chinese characters as {args.output_encoding}: "
        f"{args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
