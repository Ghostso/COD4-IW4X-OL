# -*- coding: utf-8 -*-
"""BA-09 dwRoomMessage 全族 vftable 布局 + 槽反汇编.

dwRoomMessageStartGame 的 vftable 是"串接"的: 它包含本类与所有基类的槽.
按出现顺序 (从已知的基类 vftable 对照), 可切出各层的 [ser, deser, meta] 三元组.
"""
import struct
import sys

import capstone

IMG = r"E:\codol_re\client_image_20261027.bin"
BASE = 0x400000
d = open(IMG, "rb").read()
N = len(d)
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def u4(o):
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def cstr(off, mx=200):
    e = d.find(b"\x00", off, min(off + mx, N))
    return d[off:e].decode("latin1", "replace") if e > 0 else ""


def td(rva):
    return cstr(rva + 8, 200)


def slots(vt_rva):
    out = []
    p = vt_rva
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


def dis(fn_va, limit=30):
    off = fn_va - BASE
    if not (0 <= off < N):
        return ["<out>"]
    out = []
    for ins in CS.disasm(d[off:off + 0x400], fn_va):
        note = ""
        for tok in ins.op_str.split(","):
            tok = tok.strip()
            if tok.startswith("0x"):
                try:
                    v = int(tok, 16)
                except ValueError:
                    continue
                if BASE + 0x1000 <= v < BASE + N:
                    s = cstr(v - BASE, 64)
                    if s and all(33 <= ord(c) < 127 for c in s) and len(s) >= 3:
                        note = '  ; "%s"' % s
        out.append("%08X %-12s %s %s%s" % (ins.address, ins.bytes.hex(),
                                           ins.mnemonic, ins.op_str, note))
        if ins.mnemonic in ("ret", "retn"):
            break
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    vt = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x009C751C
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    sl = slots(vt)
    print("vftable RVA 0x%08X  %d 槽" % (vt, len(sl)))
    for i, v in enumerate(sl):
        print("\n[%3d] 0x%08X" % (i, v))
        for ln in dis(v, limit):
            print("      " + ln)
