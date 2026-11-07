# -*- coding: utf-8 -*-
"""Dump raw bytes/ascii around the EXE net-string references; measure section entropy
in windows; look for a pointer table to net-command strings. Read-only."""
import sys, os, struct, collections, math, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
pe=pefile.PE(data=data, fast_load=False)
ib=pe.OPTIONAL_HEADER.ImageBase
print("ImageBase=%08x SizeOfImage=%08x EntryPoint=%08x" % (ib, pe.OPTIONAL_HEADER.SizeOfImage, pe.OPTIONAL_HEADER.AddressOfEntryPoint))
SECS=[(s.VirtualAddress,s.VirtualAddress+s.Misc_VirtualSize,s.PointerToRawData,s.PointerToRawData+s.SizeOfRawData,s.Name.rstrip(b'\0').decode('latin1'),s.Characteristics) for s in pe.sections]

def dump(o,n,label):
    print("### %s file=%08x" % (label, o))
    for k in range(0,n,16):
        row=data[o+k:o+k+16]
        asc="".join(chr(c) if 32<=c<127 else "." for c in row)
        print("  %08x  %-47s  %s" % (o+k, row.hex(), asc))
dump(0x132bf0,0x50,"connectResponse ref site")
dump(0x132050,0x40,"challengeResponse ref site")
dump(0x132c00,0x30,"second ref")

def ent(b):
    if not b: return 0
    c=collections.Counter(b)
    return -sum((v/len(b))*math.log2(v/len(b)) for v in c.values())
print("\n=== entropy windows in first .tp3 (CODE, raw 0x1000..0x594000) ===")
for base in range(0x1000, 0x594000, 0x80000):
    w=data[base:base+0x80000]
    print("  %08x  entropy=%.3f  E8=%d E9=%d prolog=%d" % (base, ent(w), w.count(0xE8), w.count(0xE9), w.count(b"\x55\x8b\xec")))
