#!/usr/bin/env python3
"""s138_a_branches: disassemble dispatcher + every unique jump-table target.
Usage: python -I tools/s138_a_branches.py
"""
import struct
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def cstr(va, ml=90):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def dis(va, n, stop_after_jmp=True):
    f = va - VA
    code = d[f:f + n]
    out = []
    for ins in md.disasm(code, va):
        line = "  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
            s = cstr(int(m.group(1), 16))
            if s:
                line += "   ; '%s'" % s
        out.append(line)
        if stop_after_jmp and ins.mnemonic in ("jmp", "ret", "retn"):
            break
    print("\n".join(out))


print("=" * 70)
print("dispatcher 0xB82CF0..0xB82D60")
dis(0xB82CF0, 0x80, stop_after_jmp=False)

T = 0xB83744
targets = []
for k in range(76):
    v = u32(T + 4 * k)
    if v not in targets:
        targets.append(v)

# count occurrences
print("\n" + "=" * 70)
print("unique targets: %d" % len(targets))
for t in targets:
    ops = [k + 1 for k in range(76) if u32(T + 4 * k) == t]
    print("\n--- target 0x%08X  ops=%s" % (t, ",".join("0x%02X" % o for o in ops)))
    dis(t, 0x50)
