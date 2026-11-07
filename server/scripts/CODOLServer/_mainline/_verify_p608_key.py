"""Verify [p608+0x9C] as the AES key against a captured sent_85 head."""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

from Crypto.Cipher import AES


def main() -> int:
    stdout = Path(sys.argv[1])
    logs_root = Path(sys.argv[2])
    obj = None
    for line in stdout.read_text(encoding="utf-8", errors="replace").splitlines():
        if "POST83_PROVIDER608" not in line:
            continue
        match = re.search(r"obj608=([0-9a-f]+)", line)
        if match:
            obj = bytes.fromhex(match.group(1))
            break
    if not obj:
        print("no obj608")
        return 1
    key = (bytes.fromhex(sys.argv[3]) if len(sys.argv) > 3
           else obj[0x9C:0x9C + 16])
    head = None
    where = None
    for directory in sorted(logs_root.glob("E57A5C_20261001_155*"),
                           key=lambda p: p.stat().st_mtime, reverse=True):
        path = directory / "plain.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("event") == "sent_85" and event.get("len") == 772:
                head = bytes.fromhex(event["hex"])
                where = directory
                break
        if head:
            break
    print("key", key.hex(), "logged", where)
    for opcode, tail in ((0x87, b"\x01"), (0x89, b"\x01\x01\x00")):
        body = bytes([opcode]) + tail
        plain = struct.pack("<I", 4) + body + b"\x00" * (352 - 4 - len(body))
        cipher = AES.new(key, AES.MODE_CBC, b"\x00" * 16).encrypt(plain)
        print(hex(opcode), "match38", cipher[:38] == head[26:64])
        print("  computed", cipher[:38].hex())
        print("  logged  ", head[26:64].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
