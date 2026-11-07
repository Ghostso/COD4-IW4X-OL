#!/usr/bin/env python3
"""Verify the client-side lobby 0x85 MAC from a same-run object dump + log."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import struct
from pathlib import Path


TABLE = bytes.fromhex(
    "411309ae3fa3bcf31872eabc093211cc124254f4"
)
IDX = bytes([
    0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00, 0x02, 0x03,
    0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05, 0x12, 0x06, 0x0C, 0x0F,
])

FRAME_TYPE = 0xAB
OPCODE_085 = 0x85


def key_from_connection_object(obj: bytes) -> bytes:
    if len(obj) < 0x620:
        raise ValueError("object dump is shorter than 0x620 bytes")
    src = obj[0x60C:0x620]
    return bytes(TABLE[IDX[i]] ^ src[i] for i in range(20))


def iter_recorded_frames(log_path: Path):
    blob = bytearray()
    for line in log_path.open(encoding="utf-8", errors="replace"):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") != "hold_recv":
            continue
        blob += bytes.fromhex(record.get("hex", "").replace(" ", ""))

    pos = 0
    data = bytes(blob)
    while pos + 6 <= len(data):
        frame_len = struct.unpack_from("<I", data, pos)[0]
        end = pos + 4 + frame_len
        if frame_len < 6 or end > len(data):
            break
        frame = data[pos:end]
        if frame[4] == FRAME_TYPE and frame[5] == OPCODE_085:
            yield pos, frame
        pos = end


def verify(obj_path: Path, log_path: Path) -> int:
    key = key_from_connection_object(obj_path.read_bytes())
    print(f"obj={obj_path}")
    print(f"log={log_path}")
    print(f"key2={key.hex()}")

    total = 0
    hits = 0
    for offset, frame in iter_recorded_frames(log_path):
        if len(frame) <= 8:
            continue
        total += 1
        expected = hmac.new(key, frame[:-8], hashlib.sha1).digest()[:8]
        actual = frame[-8:]
        ok = expected == actual
        hits += int(ok)
        seq = struct.unpack_from("<I", frame, 6)[0]
        print(
            f"seq={seq} offset={offset} len={len(frame)} "
            f"tag={actual.hex()} calc={expected.hex()} "
            f"{'HIT' if ok else 'MISS'}"
        )

    print(f"frames={total} hits={hits}")
    return 0 if total > 0 and hits == total else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--obj", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()
    return verify(Path(args.obj), Path(args.log))


if __name__ == "__main__":
    raise SystemExit(main())
