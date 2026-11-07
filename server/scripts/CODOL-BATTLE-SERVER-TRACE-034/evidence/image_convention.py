import struct, hashlib
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG,'rb').read()
print("file size = 0x%X (%d)" % (len(d), len(d)))
print("MZ at offset 0:", d[:2])
print()
print("Addressing check: is the file a PE where offset==VA, or a flat dump?")
print("  d[0:2]      =", d[0:2])
print("  d[0x128:0x12C] =", d[0x128:0x12C], "(PE sig if this is a normal PE)")
print("  d[0x467520:0x467530] =", d[0x467520:0x467530].hex())
print()
# Does VA==offset hold? Compare section RawPtr vs VA from our earlier read
print("Section table (correct):")
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe+6)[0]
sizeopt = struct.unpack_from("<H", d, pe+20)[0]
opt = pe+24; so = opt+sizeopt
for i in range(nsec):
    o=so+40*i
    nm=d[o:o+8].rstrip(b'\x00').decode('latin1','replace')
    vsz,va,rsz,raddr=struct.unpack_from("<IIII",d,o+8)
    print("   %-10s VA=%08X RawPtr=%08X  equal=%s" % (nm,va,raddr,va==raddr))
print()
print("0x400C370 within file?", 0x400C370 < len(d))
# search for a plausible readBit: find 'readBits' caller pattern and bit-read fn
print()
print("Looking for the primitive bit reader near readBits:")
for cand in (0x5A0C30,0x5A0C70,0x400C37,0x5A0C37):
    print("   candidate %08X -> %s" % (cand, d[cand:cand+12].hex() if cand<len(d) else "OUT_OF_RANGE"))
