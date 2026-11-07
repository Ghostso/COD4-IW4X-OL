"""Sweep AES key windows from the p604/p608 provider dumps.

The unknown is now the AES key actually used by the inbound path.  The
observer logs the first 0x100 bytes of both provider objects, so try every
16/20/24/32-byte window inside them as an AES key, across the usual modes and
the frame-buffer slices, and look for the inbound opcode marker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Crypto.Cipher import AES


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
    import re
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


def slices(frame: bytes):
    yield "frame[4:-8]", frame[4:-8]
    yield "frame[10:-8]", frame[10:-8]
    yield "frame[26:-8]", frame[26:-8]
    yield "frame[4:382]", frame[4:382]


def score(pt: bytes):
    # Prefer the exact opcode position the validator compares.
    if len(pt) >= 5 and pt[4] in (0x87, 0x89):
        return 3
    if 0x89 in pt[:96] or 0x87 in pt[:96]:
        return 2
    printable = sum(32 <= b < 127 for b in pt[:64])
    if printable >= 28:
        return 1
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: _aes_key_sweep.py <plain.jsonl> <aboprobe.stdout>")
        return 2
    frame = load_frame(Path(sys.argv[1]))
    p604, p608 = load_providers(Path(sys.argv[2]))
    if not frame or not p604 or not p608:
        print("missing frame or provider dump")
        return 1
    block16 = frame[10:26]
    ivs = (("iv=0", b"\x00" * 16), ("iv=frame16", block16))
    modes = (("ECB", AES.MODE_ECB), ("CBC", AES.MODE_CBC),
             ("OFB", AES.MODE_OFB), ("CFB", AES.MODE_CFB))
    hits = 0
    for provider, buf in (("p604", p604), ("p608", p608)):
        for off, size, key in windows(buf):
            if len(key) not in (16, 24, 32):
                continue
            for msg_name, msg in slices(frame):
                if len(msg) == 0:
                    continue
                for mode_name, mode in modes:
                    for iv_name, iv in ivs:
                        try:
                            if mode == AES.MODE_ECB:
                                pt = AES.new(key, mode).decrypt(msg)
                            else:
                                pt = AES.new(key, mode, iv).decrypt(msg)
                        except Exception:
                            continue
                        rank = score(pt)
                        if rank >= 2:
                            hits += 1
                            print(f"HIT rank={rank} {provider}+0x{off:x} "
                                  f"key={size}B {mode_name} {iv_name} "
                                  f"{msg_name}")
                            print("  key ", key.hex())
                            print("  head", pt[:64].hex())
                            print("  text",
                                  ''.join(chr(b) if 32 <= b < 127 else '.'
                                          for b in pt[:64]))
    if not hits:
        print("NO_HIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
