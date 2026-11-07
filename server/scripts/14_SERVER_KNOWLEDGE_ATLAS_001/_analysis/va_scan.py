import pefile, struct
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data = open(p,"rb").read()
pe = pefile.PE(p, fast_load=True)
secs=[]
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((nm,s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))

def sec_of(va):
    for nm,va0,vs,rp,rs in secs:
        if va0 <= va < va0+max(vs,rs):
            return nm
    return None

# classify every u32 in the image: does it look like a VA into the image?
lo, hi = 0x400000, 0x400000+pe.OPTIONAL_HEADER.SizeOfImage
print("=== VA-like u32 scan of whole raw file ===")
counts={}
hits_texteref=[]
targets={0x4A2E50:"0xA2E50(VA)",0x4A2D90:"0xA2D90(VA)"}
for off in range(0, len(data)-4):
    v = struct.unpack_from("<I", data, off)[0]
    if lo <= v < hi:
        s = sec_of(v-0x400000)
        counts[s]=counts.get(s,0)+1
print("VA-like u32 by target section:")
for k,v in sorted(counts.items(), key=lambda x:-x[1]):
    print("  %-10s %d" % (k, v))

for tv,label in targets.items():
    pat = struct.pack("<I", tv)
    idxs=[]; start=0
    while True:
        i = data.find(pat, start)
        if i<0: break
        idxs.append(i); start=i+1
    print("\n%s little-endian occurrences: %d" % (label, len(idxs)))
    for i in idxs[:20]:
        s=sec_of(i)
        print("    off=0x%X (%s)" % (i, s))