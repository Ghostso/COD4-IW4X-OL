"""Decrypt the client's own post-stable 0x85 frames using the injected zero key."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Crypto.Cipher import AES


def main() -> int:
    log = Path(sys.argv[1])
    frames = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 100:
            raw = bytes.fromhex(ev["hex"])
            if len(raw) >= 6 and raw[5] == 0x85:
                frames.append((ev.get("ts"), raw))
    key = bytes(16)
    for idx, (ts, frame) in enumerate(frames):
        print(f"--- frame {idx} len={len(frame)} ts={ts} ---")
        print("head", frame[:26].hex())
        ct = frame[26:-8]
        print("ct_len", len(ct), "mod16", len(ct) % 16)
        usable = ct[:len(ct) // 16 * 16]
        pt = AES.new(key, AES.MODE_CBC, frame[10:26]).decrypt(usable)
        print("plain", pt[:96].hex())
        print("text ", ''.join(chr(b) if 32 <= b < 127 else '.'
                               for b in pt[:96]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
