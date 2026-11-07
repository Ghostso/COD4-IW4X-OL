#!/usr/bin/env python3
"""s138_obscalls: per dispatcher case, list all indirect virtual calls of the form
   mov X,[reg+disp]  ... call X   (observer/room virtual slots) with the base register source.
Also list direct helper calls (call 0x...) and key global writes in the case body.
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
    en = starts[i + 1] if i + 1 < len(starts) else END
    if st == 0x636F02:
        continue  # epilogue only
    ins = list(md.disasm(d[st - VA:en - VA], st))
    slots = []
    pending = {}   # reg -> (base_reg, disp, addr)
    directs = []
    for x in ins:
        s = x.op_str
        m = re.match(r"^(\w+), dword ptr \[(\w+) \+ (0x[0-9a-f]+)\]$", s)
        m2 = re.match(r"^(\w+), dword ptr \[(\w+)\]$", s)
        if x.mnemonic == "mov" and m:
            pending[m.group(1)] = (m.group(2), int(m.group(3), 16))
        elif x.mnemonic == "mov" and m2:
            pending[m2.group(1)] = (m2.group(2), 0)
        elif x.mnemonic == "call" and s in pending:
            base, disp = pending[s]
            slots.append((x.address, s, base, disp))
            pending = {}
        elif x.mnemonic == "call":
            m3 = re.match(r"^(0x[0-9a-f]+)$", s)
            if m3:
                directs.append((x.address, int(m3.group(1), 16)))
            if s.startswith("dword ptr ["):
                directs.append((x.address, -1))
            pending = {}
        elif x.mnemonic in ("mov", "lea", "add", "sub", "imul", "push", "pop", "test", "cmp", "fldz", "fstp", "movzx", "movsx", "jmp", "je", "jne", "jle", "jl", "jge", "ja", "jns"):
            pass
        else:
            pass
    print("== types %-24s 0x%08X .. 0x%08X" % (",".join(hex(t) for t in tbl[st]), st, en))
    for a, reg, base, disp in slots:
        tag = ""
        if base == "ebx":
            tag = "ROOM(this) slot+0x%X" % disp
        else:
            tag = "OBS(%s) slot+0x%X" % (base, disp)
        print("     0x%08X  call %s   <- %s" % (a, reg, tag))
    uniq = sorted({t for _, t in directs if t > 0})
    print("     direct calls: %s" % ", ".join(hex(t) for t in uniq))
    print()
