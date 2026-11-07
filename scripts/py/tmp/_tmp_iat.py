import struct, sys
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d = open(p,'rb').read()
e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
assert d[e_lfanew:e_lfanew+4] == b'PE\0\0'
nsec = struct.unpack_from('<H', d, e_lfanew+6)[0]
opt = e_lfanew + 24
magic = struct.unpack_from('<H', d, opt)[0]
print("magic=0x%X nsec=%d" % (magic, nsec))
if magic == 0x10b:
    imgbase = struct.unpack_from('<I', d, opt+28)[0]
    ddir = opt + 96
else:
    imgbase = struct.unpack_from('<Q', d, opt+24)[0]
    ddir = opt + 112
print("ImageBase=0x%X" % imgbase)
secs = []
so = opt + struct.unpack_from('<H', d, e_lfanew+20)[0]
for i in range(nsec):
    off = so + i*40
    name = d[off:off+8].rstrip(b'\0').decode()
    vsz, va, rsz, raw = struct.unpack_from('<IIII', d, off+8)
    secs.append((name, va, vsz, raw, rsz))
    print("  %-8s VA=0x%08X VSZ=0x%08X RAW=0x%08X" % (name, va, vsz, raw))

def r2o(rva):
    for name, va, vsz, raw, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None

# import dir index 1
imp_rva, imp_sz = struct.unpack_from('<II', d, ddir + 1*8)
print("\nImportDir RVA=0x%X size=0x%X" % (imp_rva, imp_sz))
off = r2o(imp_rva)
idx = 0
while True:
    ent = d[off+idx*20: off+idx*20+20]
    if len(ent) < 20: break
    oft, ts, fc, name_rva, ft = struct.unpack('<IIIII', ent)
    if oft == 0 and ft == 0 and name_rva == 0: break
    no = r2o(name_rva)
    dllname = d[no:d.index(b'\0', no)].decode('latin1') if no is not None else "?"
    thr = ft if ft else oft
    to = r2o(thr)
    j = 0
    while True:
        v = struct.unpack_from('<I', d, to + j*4)[0]
        if v == 0: break
        iat_va = imgbase + ft + j*4
        if 0x10B022F4 - 4 <= iat_va <= 0x10B022F4 + 4:
            if v & 0x80000000:
                print("  ★ IAT 0x%08X -> %s #%d" % (iat_va, dllname, v & 0xFFFF))
            else:
                hn = r2o(v & 0x7FFFFFFF)
                nm = d[hn+2:d.index(b'\0', hn+2)].decode('latin1')
                print("  ★ IAT 0x%08X -> %s!%s" % (iat_va, dllname, nm))
        j += 1
    idx += 1
