"""Brute-force the inner AES layer of the captured 0x85 frame.

The MAC is already solved.  What remains is the inner payload the validator
parses at 0xBA3AE0 (opcode must be 0x87 or 0x89).  Sweep every small key
window inside the frame and every plausible ciphertext start offset.
"""
from __future__ import annotations

import json
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


def key_windows(frame: bytes):
    for size in (16, 24, 32):
        for off in range(0, 96 - size + 1):
            yield off, size, frame[off:off + size]


def score(pt: bytes):
    if len(pt) < 8:
        return 0
    claimed = int.from_bytes(pt[:4], "little")
    opcode = pt[4]
    # Strong criterion: the validator at 0xBA3AE0 reads the opcode at this
    # exact position, so demand BOTH a sane little-endian length and the
    # marker byte.  A lone 0x89 in otherwise random bytes is not evidence.
    if opcode in (0x87, 0x89) and 5 <= claimed <= len(pt):
        return 4
    return 0


def main() -> int:
    frame = load_frame(Path(sys.argv[1]))
    if not frame:
        print("no frame")
        return 1
    print("frame", len(frame))
    found = 0
    for key_off, key_size, key in key_windows(frame):
        for ct_start in range(8, 41):
            ct = frame[ct_start:-8]
            if len(ct) < 16:
                continue
            for mode_name, mode in (("ECB", AES.MODE_ECB),
                                    ("CBC", AES.MODE_CBC),
                                    ("OFB", AES.MODE_OFB),
                                    ("CFB", AES.MODE_CFB)):
                for iv_name, iv in (("iv=0", b"\x00" * 16),
                                    ("iv=frame16", frame[10:26]),
                                    ("iv=self", key[:16])):
                    try:
                        if mode == AES.MODE_ECB:
                            pt = AES.new(key, mode).decrypt(
                                ct[:len(ct) // 16 * 16])
                        else:
                            pt = AES.new(key, mode, iv).decrypt(
                                ct[:len(ct) // 16 * 16])
                    except Exception:
                        continue
                    rank = score(pt)
                    if rank >= 3:
                        found += 1
                        print(f"HIT rank={rank} key=frame[{key_off}:0x"
                              f"{key_off+key_size:x}] {mode_name} "
                              f"{iv_name} ct_start={ct_start}")
                        print("  key ", key.hex())
                        print("  head", pt[:64].hex())
                        print("  text",
                              ''.join(chr(b) if 32 <= b < 127 else '.'
                                      for b in pt[:64]))
    print("HITS", found)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
