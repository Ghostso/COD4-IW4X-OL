# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
d = pe.data
e = struct.unpack_from("<I", d, 0x3C)[0]
coff = e + 4
nsec, = struct.unpack_from("<H", d, coff + 2)
optsize, = struct.unpack_from("<H", d, coff + 16)
chars, = struct.unpack_from("<H", d, coff + 18)
opt = coff + 20
magic, = struct.unpack_from("<H", d, opt)
print("e_lfanew=0x%X nsec=%d optsize=%d characteristics=0x%X magic=0x%X" % (e, nsec, optsize, chars, magic))
print("sections:", [(s.name, hex(s.vaddr), hex(s.vsize), hex(s.rawptr), hex(s.rawsize)) for s in pe.sections])
dd = opt + (112 if magic == 0x20B else 96)
print("data dirs start at file off 0x%X" % dd)
names = ["Export","Import","Resource","Exception","Certificate","BaseReloc","Debug","Arch","GlobalPtr","TLS","LoadConfig","BoundImport","IAT","DelayImport","CLR","Reserved"]
for i, nm in enumerate(names):
    rva, sz = struct.unpack_from("<II", d, dd + i * 8)
    if rva or sz:
        print("  [%2d] %-12s rva=0x%08X size=%d" % (i, nm, rva, sz))
