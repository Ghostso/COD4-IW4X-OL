#!/usr/bin/env python3
"""s138_a_slots2: robust vt[slot] extraction:
  load D=[reg+0x4F0]; then V=[D]; then take [V+NN] and either call it or push it.
Also reports every string constant / callback in the executor.
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


def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def dis(va, n):
    return list(md.disasm(d[va - VA:va - VA + n], va))


def slots_in(ins_list):
    """Return list of (slot, at, objreg)."""
    base_reg = None
    deref_reg = None
    out = []
    for x in ins_list:
        t = x.op_str
        if x.mnemonic == "mov" and "0x4f0" in t and "[" in t:
            # mov regA, dword ptr [regB + 0x4f0]
            m = re.match(r"(\w+), dword ptr \[(\w+) \+ 0x4f0\]", t)
            if m:
                base_reg = m.group(1)
                deref_reg = None
                continue
        if base_reg and x.mnemonic == "mov" and t == "%s, dword ptr [%s]" % ("edx", base_reg):
            deref_reg = "edx"
            continue
        if base_reg and x.mnemonic == "mov" and t == "%s, dword ptr [%s]" % ("eax", base_reg):
            deref_reg = "eax"
            continue
        if deref_reg and x.mnemonic == "mov":
            m = re.match(r"(\w+), dword ptr \[%s \+ (0x[0-9a-f]+)\]" % deref_reg, t)
            if m:
                out.append((int(m.group(2), 16), x.address))
                deref_reg = None
    return out


def strings_in(ins_list):
    out = []
    for x in ins_list:
        for m in re.finditer(r"0x([0-9a-f]{5,8})", x.op_str):
            s = cstr(int(m.group(1), 16))
            if s:
                out.append(s)
    return out


def calls_in(ins_list):
    out = []
    for x in ins_list:
        if x.mnemonic == "call" and x.op_str.startswith("0x"):
            out.append(int(x.op_str, 16))
    return out


rows = []
for k in range(0x4B):
    rows.append((k + 1, u32(0xB83744 + 4 * k)))
rows.append((0x3E9, 0xB83547))
for k in range(9):
    rows.append((0x3EA + k, u32(0xB83870 + 4 * k)))

for op, t in rows:
    ins = dis(t, 0x50)
    found = slots_in(ins)
    exe = None
    if not found:
        for x in ins:
            if x.mnemonic == "call" and x.op_str.startswith("0x"):
                exe = int(x.op_str, 16)
                break
            if x.mnemonic in ("jmp", "ret"):
                break
        if exe:
            ei = dis(exe, 0x180)
            found = slots_in(ei)
    st = ""
    if found:
        st = ", ".join("vt[0x%02X]->0x%08X" % (s, u32(0xDE07A4 + s) or 0) for s, _ in found)
    ef = dis(exe, 0x180) if exe else ins
    strs = strings_in(ef)
    cs = calls_in(ef)
    print("0x%02X %-6d br=0x%08X exec=%s %s%s%s"
          % (op, op, t, ("0x%08X" % exe) if exe else "-",
             ("  " + st) if st else "",
             ("  strs=" + repr(strs[:4])) if strs else "",
             ("  calls=" + ",".join("0x%X" % c for c in cs[:6])) if cs else ""))
