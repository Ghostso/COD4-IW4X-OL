"""Offline (read-only) analysis: decode the client's own 0x85 frames.

输入：一次运行目录（含 plain.jsonl / rx.txt / tx.txt）。
输出：每条 hold_recv 0x85 帧在若干候选密钥下的 AES-CBC 明文。

目的：判断客户端在 0x83 之后发来的 0x85 到底是
  (a) DW 任务帧  inner = u32 declared | 0x86 | service | 0x03 | task | payload
  (b) 还是 0x87/0x89 一类
并顺带确定收/发两侧的 AES 密钥口径。不写任何文件、不碰游戏进程。
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lobby_server"))
from lobby_plain_probe import codec_02a0, codec_0420  # noqa: E402

from Crypto.Cipher import AES  # noqa: E402


def hexdump(b: bytes, per: int = 16) -> str:
    out = []
    for off in range(0, len(b), per):
        chunk = b[off:off + per]
        hx = " ".join(f"{c:02x}" for c in chunk)
        txt = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append(f"{off:04x}  {hx:<{per * 3}}  {txt}")
    return "\n".join(out)


def parse_85(blob: bytes):
    if len(blob) < 1 + 4 + 1 + 1 + 4 + 16 + 8:
        return None
    total = struct.unpack_from("<I", blob, 0)[0]
    marker = blob[4]
    op = blob[5]
    if marker != 0xAB or op != 0x85:
        return None
    seq = struct.unpack_from("<I", blob, 6)[0]
    iv = blob[10:26]
    tag = blob[-8:]
    cipher = blob[26:-8]
    return {"total": total, "seq": seq, "iv": iv, "tag": tag, "cipher": cipher}


def try_keys(src20: bytes) -> dict:
    c = codec_02a0(src20)
    d = codec_0420(src20)
    out = {}
    if len(c) >= 20:
        out["codec_02a0[:16]"] = c[:16]
        out["codec_02a0[4:20]"] = c[4:20]
    if len(d) >= 20:
        out["codec_0420[:16]"] = d[:16]
        out["codec_0420[4:20]"] = d[4:20]
    if len(src20) >= 16:
        out["raw[:16]"] = src20[:16]
        out["raw[4:20]"] = src20[4:20]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rundir")
    a = ap.parse_args()

    rx20 = bytes.fromhex(open(os.path.join(a.rundir, "rx.txt")).read().strip())
    tx20 = bytes.fromhex(open(os.path.join(a.rundir, "tx.txt")).read().strip())
    print(f"rx20 = {rx20.hex()}")
    print(f"tx20 = {tx20.hex()}")

    frames = []
    with open(os.path.join(a.rundir, "plain.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event") == "hold_recv":
                blob = bytes.fromhex(ev["hex"])
                # hold_recv 是 4 字节长度前缀 + 帧；可能含多帧
                off = 0
                while off + 5 <= len(blob):
                    total = struct.unpack_from("<I", blob, off)[0]
                    if total <= 0 or off + 4 + total > len(blob):
                        break
                    frames.append(blob[off:off + 4 + total])
                    off += 4 + total

    print(f"\n=== 客户端 0x85 帧：{len(frames)} 条 ===")
    keysets = {"rx": try_keys(rx20), "tx": try_keys(tx20)}
    raw = {"rx": rx20, "tx": tx20}

    for idx, fr in enumerate(frames, 1):
        info = parse_85(fr)
        if info is None:
            print(f"\n--- #{idx} 非 0x85 帧 len={len(fr)} ---")
            print(hexdump(fr[:64]))
            continue
        print(f"\n--- #{idx} seq={info['seq']} total={info['total']} "
              f"cipher={len(info['cipher'])} ---")
        for side, ks in keysets.items():
            for name, key in list(ks.items()) + [(f"{side}20[:16]", raw[side][:16])]:
                if len(key) != 16:
                    continue
                try:
                    pt = AES.new(key, AES.MODE_CBC, info["iv"]).decrypt(info["cipher"])
                except Exception as exc:  # noqa: BLE001
                    print(f"  [{side}/{name}] 解密异常 {exc}")
                    continue
                head = pt[:8]
                tag = ""
                if len(pt) >= 9 and 0x20 <= pt[8] < 0x7F:
                    tag = " printable"
                print(f"  [{side}/{name}] {key.hex()} -> {head.hex()}{tag}")
                if len(pt) >= 12 and pt[8] in (0x86, 0x87, 0x89, 0x01, 0x02):
                    print(hexdump(pt[:96], 16))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
