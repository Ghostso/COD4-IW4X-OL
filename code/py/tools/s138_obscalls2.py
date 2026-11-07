#!/usr/bin/env python3
"""s138_obscalls2: per dispatcher case, list indirect calls and whether the receiver
(ecx at call time) is `ebx` (the room, -> ROOM slot) or an observer node object (-> OBS slot).
Heuristic: track `mov ecx, <src>` immediately before the call, and the vtable reg source.
"""
import re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


T = 0x636F3C
tbl = {}
for k in range(0x2F):
    tbl.setdefault(u32(T + 4 * k), []).append(k)
starts = sorted(tbl)
END = 0x636F40

for i, st in enumerate(starts):
    if st == 0x636F02:
        continue
    en = starts[i + 1] if i + 1 < len(starts) else END
    ins = list(md.disasm(d[st - VA:en - VA], st))
    vtab = {}     # reg -> (base_label, disp)   base_label resolved later
    recv = None   # last mov ecx, X
    calls = []
    for x in ins:
        s = x.op_str
        m = re.match(r"^(\w+), dword ptr \[(\w+) \+ (0x[0-9a-f]+)\]$", s)
        m2 = re.match(r"^(\w+), dword ptr \[(\w+)\]$", s)
        if x.mnemonic == "mov" and m:
            vtab[m.group(1)] = (m.group(2), int(m.group(3), 16))
        elif x.mnemonic == "mov" and m2:
            vtab[m2.group(1)] = (m2.group(2), 0)
            if m2.group(1) == "ecx":
                recv = m2.group(2)
        elif x.mnemonic == "mov" and s.startswith("ecx, "):
            recv = s[5:]
        elif x.mnemonic == "call" and s in vtab:
            base, disp = vtab[s]
            who = "ROOM" if base in ("ebx",) or (base not in vtab) else base
            calls.append((x.address, s, base, disp, recv))
        elif x.mnemonic == "call":
            vtab = {}
    print("== types %-22s 0x%08X" % (",".join(hex(t) for t in tbl[st]), st))
    for a, reg, base, disp, recv in calls:
        kind = "ROOM" if recv in ("ebx",) else ("OBS " if recv else "?  ")
        print("     0x%08X call %-4s  via [%s+0x%X]  recv=%s -> %s slot+0x%X"
              % (a, reg, base, disp, recv, kind, disp))
