#!/usr/bin/env python3
"""137: name -> vtable (RTTI/COL) resolver + disasm helpers."""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def find_all(pat):
    out, pos = [], 0
    while True:
        i = d.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        out.append(i)
    return out


def rd(va):
    f = va - VA
    if 0 <= f < N - 4:
        return struct.unpack_from("<I", d, f)[0]
    return None


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    try:
        return d[f:e].decode("latin1")
    except Exception:
        return None


def resolve(name):
    """name string (without .?AV) -> vtables via RTTI."""
    raw = (".?AV" + name + "@@").encode()
    res = []
    for i in find_all(raw):
        strva = VA + i
        ti = strva - 8          # type_info object start
        # find COL: a dword == ti , at COL+0x0C
        for j in find_all(struct.pack("<I", ti)):
            col = VA + j - 0x0C
            vtable = col + 4    # vtable - 4 == COL
            # sanity: rd(vtable-4)==col
            if rd(vtable - 4) == col:
                # verify vtable slots mostly code
                res.append((strva, ti, col, vtable))
    return res


def dis(va, ln, label=""):
    print("=== disasm %s @0x%08X ===" % (label, va))
    f = va - VA
    for ins in md.disasm(d[f:f + ln], va):
        line = "  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(),
                                          ins.mnemonic, ins.op_str)
        for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
            v = int(tok, 16)
            if VA <= v < VA + N and v % 4 == 0:
                s = cstr(v)
                if s:
                    line += "   ; '%s'" % s
                    break
        print(line)


if __name__ == "__main__":
    for name in sys.argv[1:]:
        print("### %s" % name)
        rs = resolve(name)
        if not rs:
            print("   (no RTTI/COL found)")
        for strva, ti, col, vt in rs:
            print("   name@0x%08X ti=0x%08X COL=0x%08X vtable=0x%08X" %
                  (strva, ti, col, vt))
            for k in range(6):
                e = rd(vt + 4 * k)
                print("       vf%d = 0x%08X" % (k, e or 0))
        print()
