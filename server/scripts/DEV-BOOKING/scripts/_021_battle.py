# -*- coding: utf-8 -*-
"""021: CODOL Battle contract recovery (static only, read-only)."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import DATA, BASE, END, MD, dis, show, cstr, find_dword, direct_callers, vtable_at
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

def callers_of_iat(slot):
    """All 'call dword ptr [slot]' sites."""
    pat = bytes([0xFF, 0x15]) + struct.pack("<I", slot)
    out, i = [], DATA.find(pat)
    while i >= 0:
        out.append(BASE + i)
        i = DATA.find(pat, i + 1)
    return out

def context(va, before=10, after=4):
    insns = list(dis(va - 40, va + 40))
    idx = None
    for k, ins in enumerate(insns):
        if ins.address == va:
            idx = k; break
    if idx is None:
        print("    (context undecodable)")
        return
    for k in range(max(0, idx - before), min(len(insns), idx + after)):
        ins = insns[k]
        note = ""
        for op in ins.operands:
            if op.type == X86_OP_IMM and BASE <= op.imm < END:
                s = cstr(op.imm, 48)
                if s: note = '   ; "%s"' % s
        mark = " <<<" if ins.address == va else ""
        print("      0x%08X  %-18s %s %s%s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note, mark))

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sock":
        slot = int(sys.argv[2], 16)
        sites = callers_of_iat(slot)
        print("=== call [0x%X] : %d sites ===" % (slot, len(sites)))
        for s in sites:
            print("  --- 0x%08X" % s)
            context(s)
    elif cmd == "sweep":
        a, b = int(sys.argv[2], 16), int(sys.argv[3], 16)
        cur = a
        while cur < b:
            ins = next(MD.disasm(DATA[cur - BASE: b - BASE], cur), None)
            if ins is None:
                cur += 1; continue
            note = ""
            for op in ins.operands:
                if op.type == X86_OP_IMM and BASE <= op.imm < END:
                    s = cstr(op.imm, 48)
                    if s: note = '   ; "%s"' % s
            print("  0x%08X  %-18s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note))
            cur = ins.address + ins.size
