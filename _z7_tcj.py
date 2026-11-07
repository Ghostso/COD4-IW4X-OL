import struct
p = r"run_codol_001\sandbox_ifs1_20260923\TCJ.dll"
d = open(p,"rb").read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
mach = struct.unpack_from("<H", d, pe+4)[0]
# exports
nsec = struct.unpack_from("<H", d, pe+6)[0]
optsz = struct.unpack_from("<H", d, pe+20)[0]
optoff = pe+24
magic = struct.unpack_from("<H", d, optoff)[0]
ddoff = optoff + (96 if magic==0x10B else 112)
exp_rva, exp_sz = struct.unpack_from("<II", d, ddoff)
secs=[]; so=optoff+optsz
for i in range(nsec):
    vsize,vaddr,rsize,raddr = struct.unpack_from("<IIII", d, so+i*40+8)
    secs.append((vaddr,vsize,raddr,rsize))
def r2o(rva):
    for va,vs,ra,rs in secs:
        if va <= rva < va+max(vs,rs): return ra+(rva-va)
    return None
eo = r2o(exp_rva)
if eo:
    nfun = struct.unpack_from("<I", d, eo+0x14)[0]
    nnam = struct.unpack_from("<I", d, eo+0x18)[0]
    anp = r2o(struct.unpack_from("<I", d, eo+0x20)[0])
    print("TCJ.dll exports:", nfun, "functions")
    for i in range(min(nfun, 20)):
        no = r2o(struct.unpack_from("<I", d, anp+i*4)[0])
        end = d.index(b"\x00", no)
        print("   ", d[no:end].decode())
else:
    print("TCJ.dll: no exports (size=%d)" % len(d))
# strings hint
import re
ss = set()
for m in re.finditer(rb"[A-Za-z0-9_.\\/-]{6,60}", d):
    s = m.group().decode()
    if any(k in s.lower() for k in ("tas","tcj","tenio","sign","dsa","rsa")):
        ss.add(s)
print("hint strings:", sorted(ss)[:20])
