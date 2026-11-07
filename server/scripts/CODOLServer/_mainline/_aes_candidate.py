"""Focused check of the one rank-3 hit from _aes_key_sweep.

Candidate:
  key    = p608 + 0xDD, 32 bytes
  mode   = AES-CBC
  iv     = frame[10:26]
  output = AES-CBC-decrypt(frame[10:-8])

The sweep saw byte 4 == 0x89.  This script prints the complete plaintext
shape and checks the surrounding fields so the hit can be accepted or rejected.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from Crypto.Cipher import AES


def load_frame(path: Path):
    for line in path.read_text(encoding="utf-8",
                               errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def load_p608(path: Path):
    pat = re.compile(r"obj608=([0-9a-f]+)")
    for line in path.read_text(encoding="utf-8",
                               errors="replace").splitlines():
        if "POST83_PROVIDER608" not in line:
            continue
        match = pat.search(line)
        if match:
            return bytes.fromhex(match.group(1))
    return None


def dump(label: str, data: bytes):
    print(f"{label} len={len(data)}")
    for off in range(0, min(len(data), 256), 16):
        chunk = data[off:off + 16]
        text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {off:04x}  {chunk.hex()}  {text}")


def main() -> int:
    plain = Path(sys.argv[1])
    stdout = Path(sys.argv[2])
    frame = load_frame(plain)
    p608 = load_p608(stdout)
    if not frame or not p608:
        print("missing frame or p608")
        return 1
    key = p608[0xDD:0xDD + 32]
    iv = frame[10:26]
    print("frame", len(frame), "p608", len(p608))
    print("key", key.hex())
    print("iv ", iv.hex())

    candidates = (
        ("frame[10:-8]", frame[10:-8]),
        ("frame[10:382]", frame[10:382]),
        ("frame[26:-8]", frame[26:-8]),
        ("frame[4:-8]", frame[4:-8]),
    )
    for label, msg in candidates:
        if len(msg) % 16:
            print(f"{label}: skip len={len(msg)} not 16-aligned")
            continue
        pt = AES.new(key, AES.MODE_CBC, iv).decrypt(msg)
        dump(label, pt)
        if len(pt) >= 5:
            print(f"  u32@0={int.from_bytes(pt[:4], 'little')} "
                  f"u32@2={int.from_bytes(pt[2:6], 'little')} "
                  f"opcode@4=0x{pt[4]:02x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
