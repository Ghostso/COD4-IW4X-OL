"""Offline (read-only): decode every client 0x85 task frame.

密钥口径来自 F: 盘已验证实现（provider 对象 +0x9C 的 key schedule 首 16 字节），
而不是本仓库此前用的 codec_02a0(obj+0x620)[4:20]。

客户端任务明文: u32 declared | 0x86 | service | ver | task | payload
"""

from __future__ import annotations

import json
import os
import struct
import sys

from Crypto.Cipher import AES


def frames_from(rundir: str):
    out = []
    with open(os.path.join(rundir, "plain.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("event") not in ("hold_recv", "recv"):
                continue
            blob = bytes.fromhex(ev["hex"])
            off = 0
            while off + 5 <= len(blob):
                total = struct.unpack_from("<I", blob, off)[0]
                if total <= 0 or off + 4 + total > len(blob):
                    break
                out.append(blob[off:off + 4 + total])
                off += 4 + total
    return out


def show(pt: bytes, limit: int = 160) -> str:
    d = pt[:limit]
    return " ".join(f"{b:02x}" for b in d) + (" ..." if len(pt) > limit else "")


def main() -> int:
    rundir = sys.argv[1]
    key = bytes.fromhex(sys.argv[2])
    frames = frames_from(rundir)
    print(f"key={key.hex()} frames={len(frames)}\n")
    for i, fr in enumerate(frames):
        if len(fr) < 34 or fr[4] != 0xAB or fr[5] != 0x85:
            print(f"#{i} len={len(fr)} not 0x85")
            continue
        total = struct.unpack_from("<I", fr, 0)[0]
        seq = struct.unpack_from("<I", fr, 6)[0]
        iv, ct = fr[10:26], fr[26:4 + total - 8]
        if len(ct) % 16 or not ct:
            print(f"#{i} seq={seq} bad cipher len {len(ct)}")
            continue
        pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        declared = struct.unpack_from("<I", pt, 0)[0]
        print(f"#{i} seq={seq} total={total} declared={declared} "
              f"marker=0x{pt[4]:02x} service={pt[5]} ver={pt[6]} task={pt[7]}")
        pay = pt[8:8 + max(0, declared - 3)] if declared >= 3 else b""
        print(f"   payload({len(pay)}): {show(pay)}")
        txt = bytes(c for c in pay if 32 <= c < 127)
        if len(txt) > 8:
            print(f"   ascii: {txt[:160]!r}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
