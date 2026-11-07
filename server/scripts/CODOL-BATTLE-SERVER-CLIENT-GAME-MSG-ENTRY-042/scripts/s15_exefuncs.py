# -*- coding: utf-8 -*-
"""Find function boundaries near EXE references to net-command strings, then
disassemble cleanly. Read-only."""
import sys, os, struct, capstone, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32); md.detail=True

def find_prologue_before(off, back=0xC00):
    i=off
    lo=max(0x1000, off-back)
    best=None
    while i>lo:
        if data[i-3:i]==b"\x55\x8b\xec":
            best=i-3; 
            # keep scanning a little more for an even earlier start? Return the nearest.
            return best
        i-=1
    return None

def dis_from(off, n, label):
    print("### %s  file=%08x RVA=%08x" % (label, off, off))
    for i in md.disasm(data[off:off+n], IB+off):
        print("   %08x  %-20s %-8s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))

# ref sites found earlier
for off,label in [(0x132c11,"ref connectResponse (0xdbff0c)"),
                  (0x132b5c,"ref challengeResponse"),
                  (0x13205d,"ref getchallenge fmt"),
                  (0x3ab2a,"ref gamestateupdate #1"),
                  (0x509af,"ref gamestateupdate #2")]:
    p=find_prologue_before(off)
    print("=== %s : nearest prologue before = %s (dist %d) ===" % (label, hex(p) if p else None, (off-p) if p else -1))
    if p: dis_from(p, 0x140, label)
    print()
