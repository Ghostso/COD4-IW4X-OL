"""Locate the 0x85 MAC key from the provider object dumps.

The observer logs POST83_PROVIDERS / POST83_PROVIDER608 with the first
0x100 bytes of p604 and p608.  The frame tail is 8 bytes and the verified
send-side construction is HMAC-SHA1(key, message)[:8].  This script tries
every 16/20/32-byte window inside those dumps as the key, against several
plausible message slices, and reports any exact tail-byte match.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from pathlib import Path


def load_frame(log_path: Path):
    for line in log_path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def load_providers(stdout_path: Path):
    p604 = p608 = None
    pat = re.compile(r"obj(604|608)=([0-9a-f]+)")
    for line in stdout_path.read_text(encoding="utf-8",
                                      errors="replace").splitlines():
        if "POST83_PROVIDER" not in line:
            continue
        for which, hexv in pat.findall(line):
            if which == "604":
                p604 = bytes.fromhex(hexv)
            else:
                p608 = bytes.fromhex(hexv)
    return p604, p608


def windows(buf: bytes):
    for size in (16, 20, 24, 32):
        for off in range(0, max(0, len(buf) - size + 1)):
            yield off, size, buf[off:off + size]


def message_slices(frame: bytes):
    last = len(frame) - 8
    yield "frame[:-8]", frame[:last]
    yield "frame[4:-8]", frame[4:last]
    yield "frame[4:382]", frame[4:382]
    yield "frame[10:-8]", frame[10:last]
    yield "frame[26:-8]", frame[26:last]
    yield "frame[4:4+378]", frame[4:4 + 378]


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _hmac_candidates.py <plain.jsonl> <aboprobe.stdout>")
        return 2
    frame = load_frame(Path(sys.argv[1]))
    p604, p608 = load_providers(Path(sys.argv[2]))
    if not frame or not p604 or not p608:
        print("missing frame or provider dump")
        return 1
    tail = frame[-8:]
    print("frame", len(frame), "tail", tail.hex())
    print("p604", len(p604), "p608", len(p608))

    hits = []
    for label, buf in (("p604", p604), ("p608", p608)):
        for off, size, key in windows(buf):
            for msg_name, msg in message_slices(frame):
                digest = hmac.new(key, msg, hashlib.sha1).digest()
                if digest[:8] == tail:
                    hits.append((label, off, size, msg_name, key.hex(),
                                 digest.hex()))
    if not hits:
        print("NO_HMAC_MATCH")
        return 0
    for label, off, size, msg_name, key, digest in hits:
        print(f"HIT {label}+0x{off:x} key={size}B msg={msg_name}")
        print("  key   ", key)
        print("  digest", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
