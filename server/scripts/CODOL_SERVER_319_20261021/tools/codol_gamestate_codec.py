"""CODOL 3.19 gamestate/configstring codec used by Phase 2.

The layout is ported from ol-mod / CODOL-Combat-Server-v0.1:
  ServerCommandGameState = 3
  ServerCommandConfigString = 4
  ServerCommandEof = 6 (the fixture's trailing marker)

The config-string writer intentionally has a split cursor:
  * bit fields use WriteBits / Bit
  * NUL-terminated raw strings use append-only WriteBytes
This matches the 3.19 fixture byte-for-byte for the six recovered records.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = ROOT / "tests" / "fixtures" / "firingrange-gamestate.bin"


@dataclass
class ConfigString:
    index: int
    value: bytes


@dataclass
class ConfigStringBlock:
    strings: list[ConfigString] = field(default_factory=list)
    tail: bytes = b""


class Writer:
    """LSB-first writer matching Codol2697BitWriter's split raw/bit cursor."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.bit = 0

    def write_byte(self, value: int) -> None:
        self.data.append(value & 0xFF)

    def write_short(self, value: int) -> None:
        self.data += bytes((value & 0xFF, (value >> 8) & 0xFF))

    def write_long(self, value: int) -> None:
        self.data += struct.pack("<I", value & 0xFFFFFFFF)

    def write_raw(self, value: bytes) -> None:
        self.data += value

    def write_cstring(self, value: bytes) -> None:
        self.write_raw(value)
        self.write_byte(0)

    def write_bits(self, value: int, width: int) -> None:
        for i in range(width):
            if (self.bit & 7) == 0:
                self.bit = len(self.data) * 8
                self.data.append(0)
            self.data[self.bit >> 3] |= ((value >> i) & 1) << (self.bit & 7)
            self.bit += 1

    def write_index(self, index: int, previous: int, index_bits: int) -> None:
        if index == previous + 1:
            self.write_bits(1, 1)
        else:
            self.write_bits(0, 1)
            self.write_bits(index, index_bits)


class Reader:
    """Inverse split-cursor reader for ConfigStringBlock."""

    def __init__(self, data: bytes, end: int) -> None:
        self.data = data
        self.bit = end * 8
        self.end = end

    def read_bits(self, width: int) -> int:
        value = 0
        for i in range(width):
            if (self.bit & 7) == 0:
                if self.end >= len(self.data):
                    raise EOFError("bitstream out of range")
                self.bit = self.end * 8
                self.end += 1
            value |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return value

    def read_cstring(self) -> bytes:
        start = self.end
        while self.end < len(self.data) and self.data[self.end] != 0:
            self.end += 1
        if self.end >= len(self.data):
            raise EOFError("unterminated string")
        value = self.data[start:self.end]
        self.end += 1
        return value


def decode_sample(path: Path) -> tuple[dict, ConfigStringBlock, int, int]:
    data = path.read_bytes()
    if len(data) < 4:
        raise ValueError("sample too short")
    pos = 4
    command = data[pos]; pos += 1
    if command != 3:
        raise ValueError(f"expected gamestate command 3, got {command}")
    version = struct.unpack_from("<I", data, pos)[0]; pos += 4
    map_end = data.index(0, pos)
    map_name = data[pos:map_end].decode("latin1"); pos = map_end + 1
    type_end = data.index(0, pos)
    game_type = data[pos:type_end].decode("latin1"); pos = type_end + 1
    field4 = struct.unpack_from("<I", data, pos)[0]; pos += 4
    config_command = data[pos]; pos += 1
    if config_command != 4:
        raise ValueError(f"expected configstring command 4, got {config_command}")
    count = struct.unpack_from("<H", data, pos)[0]; pos += 2

    reader = Reader(data, pos)
    previous = -1
    strings: list[ConfigString] = []
    for _ in range(count):
        sequential = reader.read_bits(1)
        if sequential:
            index = previous + 1
        else:
            index = reader.read_bits(14)
        value = reader.read_cstring()
        strings.append(ConfigString(index, value))
        previous = index

    block = ConfigStringBlock(strings=strings)
    prefix = encode_config_strings(block)
    config_start = pos - 3
    block.tail = data[config_start + len(prefix):]
    return {
        "command": command,
        "version": version,
        "map": map_name,
        "game_type": game_type,
        "field4": field4,
        "config_command": config_command,
        "config_count": count,
    }, block, config_start, len(data)


def encode_config_strings(block: ConfigStringBlock) -> bytes:
    writer = Writer()
    writer.write_byte(4)
    writer.write_short(len(block.strings))
    previous = -1
    for item in block.strings:
        writer.write_index(item.index, previous, 14)
        writer.write_cstring(item.value)
        previous = item.index
    writer.write_raw(block.tail)
    return bytes(writer.data)


def encode_sample(header: dict, block: ConfigStringBlock) -> bytes:
    payload = bytearray(4)
    payload.append(header["command"])
    payload += struct.pack("<I", header["version"])
    payload += header["map"].encode("latin1") + b"\0"
    payload += header["game_type"].encode("latin1") + b"\0"
    payload += struct.pack("<I", header["field4"])
    payload += encode_config_strings(block)
    return bytes(payload)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    header, block, config_start, total = decode_sample(args.sample)
    rebuilt = encode_sample(header, block)
    exact = rebuilt == args.sample.read_bytes()
    print(f"sample={args.sample}")
    print(f"size={total} config_start=0x{config_start:X} strings={len(block.strings)}")
    print(f"map={header['map']} type={header['game_type']} field4=0x{header['field4']:08X}")
    for item in block.strings:
        preview = item.value[:32].decode("latin1", "replace")
        print(f"  index={item.index:5d} len={len(item.value):3d} value={preview!r}")
    print(f"tail={len(block.tail)} bytes")
    print(f"byte_exact_roundtrip={exact}")
    if args.json_out:
        import json
        args.json_out.write_text(json.dumps({
            "header": header,
            "strings": [{"index": x.index, "value_hex": x.value.hex()} for x in block.strings],
            "tail_hex": block.tail.hex(),
            "byte_exact_roundtrip": exact,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if exact else 1


if __name__ == "__main__":
    raise SystemExit(main())
