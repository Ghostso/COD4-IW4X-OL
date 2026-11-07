# -*- coding: utf-8 -*-
"""Test EXE code validity at 038 confirmed addresses, and map RVA<->file offset
using the section table. Read-only."""
import sys, os, capstone, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
pe=pefile.PE(data=data, fast_load=False)
IB=pe.OPTIONAL_HEADER.ImageBase
SECS=[(s.Name.rstrip(b'\0').decode('latin1'), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
print("ImageBase=%08x" % IB)
for nm,va,vs,raw,rs in SECS:
    print("  %-8s RVA=%08x VSize=%08x raw=%08x rsize=%08x  file-range=%08x..%08x" % (nm,va,vs,raw,rs,raw,raw+rs))
def rva2off(r):
    for nm,va,vs,raw,rs in SECS:
        if va<=r<va+vs:
            o=raw+(r-va)
            if o < raw+rs: return o, nm, True
            return None, nm, False
    return None, "?", False
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True
def dis_rva(rva,n,label):
    o,nm,ok=rva2off(rva)
    print("### %s RVA=%08x section=%s file=%s" % (label, rva, nm, hex(o) if o is not None else "N/A(uninit)"))
    if o is None: return
    for i in md.disasm(data[o:o+n], IB+rva):
        print("   %08x  %-18s %-8s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
for a in (0x5F830, 0x2000A0, 0x20059B, 0x1FF820):
    dis_rva(a, 0x60, "038-confirmed")
    print()
