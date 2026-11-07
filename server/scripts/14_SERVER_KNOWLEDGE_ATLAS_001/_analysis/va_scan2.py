import pefile, struct
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data = open(p,"rb").read()
pe = pefile.PE(p, fast_load=True)
IB = pe.OPTIONAL_HEADER.ImageBase
secs=[]
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((nm,s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))

def off_to_sec(off):
    for nm,va,vs,rp,rs in secs:
        if rp <= off < rp+rs: return nm
    return None

def va_to_sec(va):
    for nm,va0,vs,rp,rs in secs:
        if va0 <= va < va0+max(vs,0): return nm
    return None

lo, hi = IB, IB+pe.OPTIONAL_HEADER.SizeOfImage
counts={}   # pointer value target section
src={}      # pointer location section
for off in range(0, len(data)-4):
    v = struct.unpack_from("<I", data, off)[0]
    if lo <= v < hi:
        t = va_to_sec(v-IB) or "None"
        counts[t]=counts.get(t,0)+1
        s = off_to_sec(off) or "None"
        src[(s,t)]=src.get((s,t),0)+1
print("=== VA-like u32 by TARGET section ===")
for k,v in sorted(counts.items(), key=lambda x:-x[1]): print("  %-8s %d" % (k,v))
print("\n=== by (location section -> target section), top 15 ===")
for (s,t),v in sorted(src.items(), key=lambda x:-x[1])[:15]:
    print("  %-8s -> %-8s %d" % (s,t,v))

print("\n=== target VA/RVA search ===")
for val,label in [(0x4A2E50,"VA 0x4A2E50"),(0xA2E50,"RVA 0xA2E50"),(0x4A2D90,"VA 0x4A2D90"),(0xA2D90,"RVA 0xA2D90")]:
    pat=struct.pack("<I",val); c=0; off=0
    locs=[]
    while True:
        i=data.find(pat,off)
        if i<0: break
        locs.append(i); off=i+1
    print("  %-14s count=%d  locs(sec)=%s" % (label, len(locs), [off_to_sec(x) for x in locs[:12]]))