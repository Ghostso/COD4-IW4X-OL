import struct
p = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
d = open(p,'rb').read()
base = 0x10000000
# .idata2: VA 0x00B02000, RAW 0x00AF7C00
sec_va, sec_raw, sec_sz = 0x00B02000, 0x00AF7C00, 0x00004EBA
def rd(rva, n): return d[sec_raw + (rva - sec_va): sec_raw + (rva - sec_va) + n]
tgt = 0x00B022F4
print("=== .idata2 around target ===")
o = sec_raw + (tgt - sec_va)
for i in range(-64, 128, 16):
    chunk = d[o+i:o+i+16]
    vals = " ".join("%08X" % struct.unpack_from('<I', chunk, k)[0] for k in range(0,16,4))
    print("  +%+04X  %s   | %s" % (i, vals, chunk.hex(' ')))
print()
print("=== .idata2 head (first 0x200) ===")
h = rd(sec_va, 0x100)
for i in range(0, 0x100, 16):
    chunk = h[i:i+16]
    vals = " ".join("%08X" % struct.unpack_from('<I', chunk, k)[0] for k in range(0,16,4))
    print("  RVA %08X  %s   | %s" % (sec_va+i, vals, chunk.hex(' ')))
