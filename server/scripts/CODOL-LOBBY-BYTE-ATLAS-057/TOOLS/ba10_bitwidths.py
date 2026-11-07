# -*- coding: utf-8 -*-
"""BA-10 dwRoomMessage 全族: 每个类的 serialize/deserialize 位宽表.

对每个类:
  - 找 COL / vftable
  - 找出该 vftable 中"本类新增"的槽 (与基类 vftable 前缀相同的部分属基类)
  - 对 ser/deser 槽, 提取 push imm (位宽) 与 call 目标 (writeBits/readBits/...)

输出 CSV 表 + 人读报告.
"""
import glob
import json
import os
import re
import struct
import sys

import capstone

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")
d = open(IMG, "rb").read()
N = len(d)
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

BITFNS = {
    0x00B77B10: "writeBits",
    0x00B777C0: "writeData",
    0x00B774E0: "readBits",
    0x00B772E0: "readData",
    0x00B779A0: "newStream",
}


def u4(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def cstr(off, mx=300):
    e = d.find(b"\x00", off, min(off + mx, N))
    return d[off:e].decode("latin1", "replace") if e > 0 else ""


def all_td():
    out = {}
    for m in re.finditer(rb"\.\?A[VU][\x20-\x7E]{1,200}\x00", d):
        out[m.start() - 8] = m.group()[:-1].decode("latin1")
    return out


def find_col(td_rva):
    for target in (td_rva, td_rva + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            col = i - 12
            if col >= 0 and u4(col) == 0:
                return col
            i = d.find(pat, i + 1)
    return None


def find_vft(col):
    for target in (col, col + BASE):
        pat = struct.pack("<I", target)
        i = d.find(pat)
        while i >= 0:
            yield i + 4
            i = d.find(pat, i + 1)


def slots(vt):
    out = []
    p = vt
    while p + 4 <= N:
        v = u4(p)
        if v and BASE + 0x1000 <= v < BASE + N:
            out.append(v)
            p += 4
        else:
            break
        if len(out) > 400:
            break
    return out


def analyze_slot(fn_va):
    """提取该函数里的 (push imm, call fn) 配对."""
    off = fn_va - BASE
    if not (0 <= off < N):
        return None
    seq = []
    imm = None
    for ins in CS.disasm(d[off:off + 0x300], fn_va):
        if ins.mnemonic == "push" and ins.op_str.startswith("0x"):
            try:
                imm = int(ins.op_str, 16)
            except ValueError:
                imm = None
        elif ins.mnemonic == "call":
            t = None
            if ins.op_str.startswith("0x"):
                try:
                    t = int(ins.op_str, 16)
                except ValueError:
                    t = None
            if t in BITFNS:
                seq.append((imm, BITFNS[t]))
                imm = None
            else:
                imm = None
        elif ins.mnemonic in ("ret", "retn"):
            break
        else:
            imm = None
    return seq if seq else None


def main():
    tds = all_td()
    targets = {}
    for td, nm in tds.items():
        m = re.match(r"\.\?A[VU](dwRoomMessage\w*|dwRoom\w*|RoomListEventHandler|"
                     r"DWNotificationEventHandler|dwLobbyEventHandler|"
                     r"bdLobbyEventHandler)@@", nm)
        if m:
            targets[m.group(1)] = td

    print("命中类: %d" % len(targets))
    rows = []
    for cls in sorted(targets):
        td = targets[cls]
        col = find_col(td)
        if col is None:
            print("  %-52s NO COL" % cls)
            continue
        vts = list(find_vft(col))
        if not vts:
            print("  %-52s NO VFT" % cls)
            continue
        vt = vts[0]
        sl = slots(vt)
        info = []
        for i, v in enumerate(sl):
            sq = analyze_slot(v)
            if sq:
                info.append((i, v, sq))
        rows.append(dict(cls=cls, td=td, col=col, vt=vt, nslots=len(sl),
                         bit=[(i, "0x%08X" % v, sq) for i, v, sq in info]))
        print("\n%-52s TD=0x%08X COL=0x%08X VT=0x%08X 槽=%d 位流函数槽=%d"
              % (cls, td, col, vt, len(sl), len(info)))
        for i, v, sq in info[:8]:
            print("   [%3d] 0x%08X  %s" % (i, v, " ".join(
                "%s(%s)" % (fn, w if w is not None else "?")
                for w, fn in sq)))

    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, "ba10_bitwidths.json"), "w",
                         encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
