import struct, sys
p = r"run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe"
d = open(p,"rb").read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
assert d[pe:pe+4] == b"PE\0\0", d[pe:pe+4]
nsec = struct.unpack_from("<H", d, pe+6)[0]
optsz = struct.unpack_from("<H", d, pe+20)[0]
opt = pe + 24
magic = struct.unpack_from("<H", d, opt)[0]
base = struct.unpack_from("<I", d, opt+28)[0]
print("size=%d nsec=%d magic=0x%X imagebase=0x%X" % (len(d), nsec, magic, base))
secs=[]
off = opt + optsz
for i in range(nsec):
    s = d[off+i*40: off+(i+1)*40]
    name = s[:8].rstrip(b"\0").decode("latin1")
    vsize, vaddr, rsize, raddr = struct.unpack_from("<IIII", s, 8)
    secs.append((name, vaddr, vsize, raddr, rsize))
    print("%-8s VA=0x%08X VS=0x%08X RAW=0x%08X RS=0x%08X" % (name, vaddr, vsize, raddr, rsize))
def rva2off(rva):
    for name, va, vs, ra, rs in secs:
        if va <= rva < va + max(vs, rs):
            return ra + (rva - va)
    return None
for va, want in ((0x8037C4, 24), (0x8037D6, 12), (0x8037FA, 12), (0x803804, 12)):
    o = rva2off(va - base)
    print("VA=0x%08X off=0x%X  %s" % (va, o, d[o:o+want].hex(" ")))
