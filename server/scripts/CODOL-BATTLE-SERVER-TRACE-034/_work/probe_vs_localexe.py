import re, struct, random
EXE = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
d=open(EXE,'rb').read()
pe=struct.unpack_from("<I",d,0x3C)[0]
nsec=struct.unpack_from("<H",d,pe+6)[0]
sizeopt=struct.unpack_from("<H",d,pe+20)[0]
opt=pe+24; so=opt+sizeopt
imgbase=struct.unpack_from("<I",d,opt+28)[0]
secs=[]
print("LOCAL TARGET EXE sections:")
for i in range(nsec):
    o=so+40*i
    nm=d[o:o+8].rstrip(b'\x00'); nm="".join(chr(c) if 32<=c<127 else '?' for c in nm)
    vsz,va,rsz,raddr=struct.unpack_from("<IIII",d,o+8)
    ch=struct.unpack_from("<I",d,o+36)[0]
    secs.append((nm,va,vsz,raddr,rsz,ch))
    print("  %-9s VA=%08X VSize=%08X RawPtr=%08X RawSize=%08X ch=%08X" % (nm,va,vsz,raddr,rsz,ch))
print("  ImageBase=%08X  SizeOfImage=%08X  file size=%08X" % (imgbase,struct.unpack_from("<I",d,opt+56)[0],len(d)))
def rva_to_off(rva):
    for nm,va,vsz,raddr,rsz,ch in secs:
        if va <= rva < va+max(vsz,rsz):
            off=raddr+(rva-va)
            if 0<=off<len(d): return off,nm
    return None,None
def pro(off):
    if off is None or off<0 or off+4>len(d): return False
    b=d[off:off+4]
    return b[:3] in (b"\x55\x8b\xec",b"\x6a\xff") or b[:2] in (b"\x8b\xff",b"\x55\x8b") or b[:1]==b"\x55"
src=open(r"D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\references\client_probe\CodolNetchanTrace.py",encoding="utf-8",errors="replace").read()
rv=[(m.group(1),int(m.group(2),16)) for m in re.finditer(r"const\s+(\w+)\s*=\s*module\.base\.add\(0x([0-9A-Fa-f]+)\)", src)]
print()
print("Testing probe RVA constants against LOCAL TARGET EXE via proper PE mapping:")
hit=0; rows=[]
for n,v in rv:
    off,sec=rva_to_off(v)
    ok=pro(off)
    hit+=1 if ok else 0
    rows.append((n,v,off,sec,ok,d[off:off+6].hex() if off is not None else "OUT"))
print("  prologue hits: %d / %d" % (hit,len(rv)))
random.seed(7)
# baseline over .text-ish rva range
allr=[v for _,v in rv]
bl=0
for v in allr:
    r=random.randrange(0x1000,0x600000)
    o,_=rva_to_off(r)
    if pro(o): bl+=1
print("  random baseline in 0x1000..0x600000: %d / %d" % (bl,len(allr)))
print()
print("  %-30s %-10s %-10s %-8s %-8s %s" % ("name","RVA","fileOff","section","prolog?","first6"))
for n,v,off,sec,ok,h in rows:
    print("  %-30s %-10X %-10s %-8s %-8s %s" % (n,v,("%X"%off if off is not None else "-"),sec or "-",ok,h))
