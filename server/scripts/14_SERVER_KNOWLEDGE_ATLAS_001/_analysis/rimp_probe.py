import pefile, struct
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data = open(p,"rb").read()
pe = pefile.PE(p, fast_load=True)
secs = {}
for s in pe.sections:
    nm = s.Name.rstrip(b"\x00").decode("latin1")
    secs[nm] = (s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData)

print("=== raw file size 0x%X (%d) ===" % (len(data), len(data)))

# .data content density in its declared VA range
va,vs,rp,rs = secs[".data"]
print("\n=== .data: VA 0x%X VSize 0x%X raw 0x%X..0x%X ===" % (va,vs,rp,rp+rs))
raw = data[rp:rp+rs]
nz = sum(1 for b in raw if b != 0)
print("  raw bytes=%d non-zero=%d (%.1f%%)" % (len(raw), nz, 100.0*nz/max(1,len(raw))))
# How much of .data VA range is covered by raw?
print("  raw covers %.2f%% of declared VSize" % (100.0*rs/max(1,vs)))
# check beyond raw (would be zero-filled at load)
print("  bytes after raw region up to file-end=%d" % (len(data)-(rp+rs)))

# .rimp
va2,vs2,rp2,rs2 = secs[".rimp"]
rimp = data[rp2:rp2+rs2]
print("\n=== .rimp: VA 0x%X VSize 0x%X raw 0x%X size %d ===" % (va2,vs2,rp2,rs2))
print("  first 64 bytes:", rimp[:64].hex(" "))
print("  non-zero bytes=%d/%d" % (sum(1 for b in rimp if b), len(rimp)))
# interpret as u32 array
words = list(struct.unpack("<%dI" % (len(rimp)//4), rimp[:len(rimp)//4*4]))
uniq = len(set(words))
print("  as u32: n=%d unique=%d min=0x%X max=0x%X" % (len(words), uniq, min(words), max(words)))
print("  first 16 u32:", " ".join("0x%08X"%w for w in words[:16]))