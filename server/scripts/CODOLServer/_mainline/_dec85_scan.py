"""Offline (read-only) scan: find the AES key / frame layout for the client's 0x85.

判据：DW 客户端任务帧解密后应为 `u32 declared | 0x86 | service | 0x03 | task | payload`。
对若干候选密钥 × 若干 IV/密文起点做穷举，凡命中 plain[4]==0x86 或 plain[8]==0x03 就打印。
不写文件、不碰游戏进程。
"""

from __future__ import annotations

import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lobby_server"))
from lobby_plain_probe import codec_02a0, codec_0420  # noqa: E402

from Crypto.Cipher import AES  # noqa: E402


def key_candidates(src20: bytes, name: str):
    c = codec_02a0(src20)
    d = codec_0420(src20)
    cands = [
        (f"{name}/c02a0[:16]", c[:16]),
        (f"{name}/c02a0[4:20]", c[4:20]),
        (f"{name}/c0420[:16]", d[:16]),
        (f"{name}/c0420[4:20]", d[4:20]),
        (f"{name}/raw[:16]", src20[:16]),
        (f"{name}/raw[4:20]", src20[4:20]),
    ]
    return [(n, k) for n, k in cands if len(k) == 16]


def frames_from(rundir: str):
    out = []
    with open(os.path.join(rundir, "plain.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event") != "hold_recv":
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


def main() -> int:
    rundir = sys.argv[1]
    rx20 = bytes.fromhex(open(os.path.join(rundir, "rx.txt")).read().strip())
    tx20 = bytes.fromhex(open(os.path.join(rundir, "tx.txt")).read().strip())

    keys = key_candidates(rx20, "rx") + key_candidates(tx20, "tx")
    if len(sys.argv) > 2:
        keys += [("explicit/%d" % i, bytes.fromhex(h))
                 for i, h in enumerate(sys.argv[2:])]
    frames = frames_from(rundir)
    print(f"frames={len(frames)} keys={len(keys)}")

    hits = 0
    for fi, fr in enumerate(frames):
        if len(fr) < 12 or fr[4] != 0xAB or fr[5] != 0x85:
            continue
        total = struct.unpack_from("<I", fr, 0)[0]
        seq = struct.unpack_from("<I", fr, 6)[0]
        body = fr[10:4 + total]           # seq 之后、帧内全部
        for iv_off in range(0, 13):
            if iv_off + 16 > len(body):
                continue
            iv = body[iv_off:iv_off + 16]
            ct = body[iv_off + 16:]
            ct = ct[:len(ct) - (len(ct) % 16)]
            if not ct:
                continue
            for kname, key in keys:
                try:
                    pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
                except Exception:  # noqa: BLE001
                    continue
                ok4 = len(pt) > 4 and pt[4] == 0x86
                ok8 = len(pt) > 8 and pt[8] == 0x03
                if ok4 or ok8:
                    hits += 1
                    print(f"\nHIT frame#{fi} seq={seq} iv_off={iv_off} key={kname}"
                          f" keyhex={key.hex()} ok4={ok4} ok8={ok8}")
                    for o in range(0, min(len(pt), 80), 16):
                        ch = pt[o:o + 16]
                        print(f"  {o:04x}  " + " ".join(f"{b:02x}" for b in ch)
                              + "  " + "".join(chr(b) if 32 <= b < 127 else "." for b in ch))
    print(f"\nhits={hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
