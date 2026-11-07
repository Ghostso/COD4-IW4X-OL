# -*- coding: utf-8 -*-
import img, struct
d = img._IMG
e_lfanew = struct.unpack_from("<I", d, 0x3C)[0]
print("e_lfanew", hex(e_lfanew))
nt = d[e_lfanew:e_lfanew+4]
print("sig", nt)
coff = e_lfanew+4
machine, nsec, tds, psym, nsym, osz, chars = struct.unpack_from("<HHIIIHH", d, coff)
print("machine=%04X nsec=%d sizeofopt=%d chars=%04X" % (machine, nsec, osz, chars))
opt = coff+20
magic = struct.unpack_from("<H", d, opt)[0]
print("opt magic", hex(magic))
ImageBase = struct.unpack_from("<I", d, opt+28)[0]
SizeOfImage = struct.unpack_from("<I", d, opt+56)[0]
print("ImageBase=%08X SizeOfImage=%08X" % (ImageBase, SizeOfImage))
secoff = opt+osz
for i in range(nsec):
    o = secoff + 40*i
    name = d[o:o+8].rstrip(b"\x00")
    vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", d, o+8)
    ch = struct.unpack_from("<I", d, o+36)[0]
    print("%-10s VA=%08X VSize=%08X Raw=%08X RawSize=%08X Char=%08X" % (name.decode('latin1'), vaddr, vsize, raddr, rsize, ch))
