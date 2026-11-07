#!/usr/bin/env python3
"""s138_a_slots: precise vt[slot] extraction.
For each opcode branch, find either
  (a) direct:  mov ecx,[edi+0x4F0]; mov edx,[ecx]; mov eax,[edx+NN]; call eax
  (b) delegated: branch call X ; X body has mov ecx,[..+0x4F0]; mov edx,[ecx];
      mov edx/eax,[edx+NN] ... call
Usage: python -I tools/s138_a_slots.py
"""
import struct
import sys
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


def dis(va, n):
    return list(md.disasm(d[va - VA:va - VA + n], va))


def find_slot(ins_list):
    """walk: after seeing [..+0x4f0] load and [reg] deref, take next [reg2+0xNN]."""
    seen_base = False
    seen_deref = False
    for x in ins_list:
        t = x.op_str
        if x.mnemonic == "mov" and "0x4f0" in t:
            seen_base = True
            continue
        if seen_base and x.mnemonic == "mov" and t.startswith("edx, dword ptr [") \
                and "0x4f0" not in t and "," in t and t.count("+") == 0:
            # mov edx, [ecx]
            seen_deref = True
            continue
        if seen_deref and x.mnemonic == "mov" and "+ 0x" in t and "[edx" in t:
            try:
                return int(t.split("+")[1].split("]")[0].strip(), 16), x.address
            except ValueError:
                pass
        if seen_deref and x.mnemonic.startswith("call"):
            break
    return None, None


def analyze(target, depth=1):
    ins = dis(target, 0x50)
    slot, at = find_slot(ins)
    if slot is not None:
        return "direct", target, slot, at
    # delegated: find first call
    exe = None
    for x in ins:
        if x.mnemonic == "call" and x.op_str.startswith("0x"):
            exe = int(x.op_str, 16)
            break
        if x.mnemonic in ("jmp", "ret"):
            break
    if exe and depth:
        s2, at2 = find_slot(dis(exe, 0xA0))
        return "deleg", exe, s2, at2
    return "?", exe, None, None


rows = []
for k in range(0x4B):
    rows.append((k + 1, u32(0xB83744 + 4 * k)))
rows.append((0x3E9, 0xB83547))
for k in range(9):
    rows.append((0x3EA + k, u32(0xB83870 + 4 * k)))

print("opcode | branch | kind | exec | vt[slot] | static fn")
for op, t in rows:
    kind, exe, slot, at = analyze(t)
    conc = u32(0xDE07A4 + slot) if slot is not None else None
    print("0x%02X (%4d) | 0x%08X | %-6s | %s | %s | %s   @%s"
          % (op, op, t, kind, ("0x%08X" % exe) if exe else "-",
             ("0x%02X" % slot) if slot is not None else "-",
             ("0x%08X" % conc) if conc else "-",
             ("0x%08X" % at) if at else "-"))
