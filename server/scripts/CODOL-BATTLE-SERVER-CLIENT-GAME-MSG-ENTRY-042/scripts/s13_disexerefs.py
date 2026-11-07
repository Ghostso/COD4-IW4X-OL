# -*- coding: utf-8 -*-
"""Disassemble EXE code around the net-command string references (RVA ~0x132000).
Read-only."""
import sys, os, struct, pefile, capstone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
pe=pefile.PE(data=data, fast_load=False)
ib=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True

def dis(rva, n):
    o=rva  # first section raw==rva
    for i in md.disasm(data[o:o+n], ib+rva):
        print("  %08x  %-22s %-8s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))

print("=== RVA 0x131f80..0x132140 ===")
dis(0x131f80, 0x1c0)
print("\n=== RVA 0x132b00..0x132c80 ===")
dis(0x132b00, 0x180)
