#!/usr/bin/env python3
"""s138_cases: for each jump-table case body, find the message vtable constant written
(mov [ebp-X], 0xdcXXXX) and resolve its class name; also report case start VA."""
import re, struct, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


def cstr(va, ml=120):
    f = va - VA
    if not (0 <= f < N - 1): return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > ml: return None
    s = d[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def vtname(vt):
    col = u32(vt - 4)
    if not col: return "COL=0"
    td = u32(col + 12)
    if not td: return "?"
    nm = cstr(td + 8, 90)
    return nm or "?"


# first-pass list of case target -> scan forward for a dc7xxx constant stored
T = 0x636F3C
seen = {}
for k in range(0x2F):
    t = u32(T + 4 * k)
    seen.setdefault(t, []).append(k)
for t, ks in sorted(seen.items()):
    # bound scan: up to next case target (only among case starts <= 0x636F02)
    later = [x for x in seen if x > t]
    end = min(later) if later else t + 0x260
    span = min(end - t, 0x260)
    names = []
    for off in range(0, span):
        va = t + off
        if d[va - VA] == 0xC7 and d[va - VA + 1] == 0x85:  # mov dword [ebp-disp32], imm32
            imm = u32(va + 6)
            if imm and 0xDC7000 <= imm < 0xDC8000:
                names.append((hex(imm), vtname(imm)))
        elif d[va - VA] == 0xC7 and d[va - VA + 1] == 0x45:  # mov dword [ebp-disp8], imm32
            imm = u32(va + 3)
            if imm and 0xDC7000 <= imm < 0xDC8000:
                names.append((hex(imm), vtname(imm)))
    print("case types %-22s target 0x%08X  msgvtable=%s" % (
        ",".join(hex(x) for x in ks), t, names[:2] if names else "-"))
