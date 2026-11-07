#!/usr/bin/env python3
"""s138_targets: dump head of every jump-table target, grouped."""
import sys, re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, ml=60):
    o = va - VA
    if not (0 <= o < N - 1): return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 3: return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def dis(va, maxn=16, maxb=0x400):
    out = []
    for ins in md.disasm(d[va - VA:va - VA + maxb], va):
        s = "0x%08X %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            cs = cstr(int(m.group(1), 16))
            if cs: s += "   ; '%s'" % cs
        out.append(s)
        if ins.mnemonic.startswith("ret") or len(out) >= maxn: break
    return out


seen = {}
for k in range(0x2F):
    t = struct.unpack_from("<I", d, 0x636F3C - VA + 4 * k)[0]
    seen.setdefault(t, []).append(k)
for t, ks in sorted(seen.items()):
    print("===== target 0x%08X  types %s" % (t, ",".join(hex(x) for x in ks)))
    for l in dis(t):
        print("   " + l)
    print()
