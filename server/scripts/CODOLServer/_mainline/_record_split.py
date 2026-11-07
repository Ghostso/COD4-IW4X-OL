"""Try to parse the 0x85 body as a sequence of TLV records.

0xC737A0 reads `u32 length`, rejects length > 0x14 (20), then reads that
many bytes, so the inner structure is expected to be

    [u32 len][len bytes] [u32 len][len bytes] ...

This script walks the captured 352-byte body under that rule and reports how
far it gets.  It also tries the same walk after a few cheap transforms, and
prints the first record so the opcode (0x87 / 0x89) can be spotted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_85(log_path: Path) -> bytes | None:
    for line in log_path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def walk(data: bytes, limit: int = 0x14, label: str = ""):
    off = 0
    records = []
    while off + 4 <= len(data):
        length = int.from_bytes(data[off:off + 4], "little")
        if length == 0 or length > limit or off + 4 + length > len(data):
            break
        payload = data[off + 4:off + 4 + length]
        records.append((off, length, payload))
        off += 4 + length
        if len(records) >= 40:
            break
    covered = off
    print(f"[{label}] records={len(records)} covered={covered}/{len(data)}")
    for idx, (at, length, payload) in enumerate(records[:10]):
        head = " ".join(f"{b:02x}" for b in payload[:8])
        ops = [f"0x{b:02x}" for b in payload if b in (0x87, 0x89)]
        print(f"   #{idx} off=0x{at:03x} len={length:2d} "
              f"payload={head}{' ...' if length > 8 else ''} "
              f"opcodes={ops}")
    return records, covered


def main() -> int:
    log = Path(sys.argv[1])
    frame = load_85(log)
    if not frame:
        print("no 0x85 frame in", log)
        return 1
    body = frame[26:-8]
    print(f"frame={len(frame)} body={len(body)} "
          f"mod16={len(body) % 16}")
    walk(body, 0x14, "raw, len<=20")
    walk(body, 0x40, "raw, len<=64")

    key = bytes.fromhex("d10f36957daff487a30f1a79ac9b23db08904b1e")[:16]
    try:
        from Crypto.Cipher import AES
    except Exception:
        print("pycryptodome missing; skipping transform probes")
        return 0

    transforms = {
        "aes-ecb-dec": lambda d: AES.new(key, AES.MODE_ECB).decrypt(d),
        "aes-cbc0-dec": lambda d: AES.new(key, AES.MODE_CBC,
                                          b"\x00" * 16).decrypt(d),
        "aes-ofb0-dec": lambda d: AES.new(key, AES.MODE_OFB,
                                          b"\x00" * 16).decrypt(d),
    }
    for name, fn in transforms.items():
        try:
            walk(fn(body), 0x14, name)
        except Exception as exc:
            print(f"[{name}] ERR {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
