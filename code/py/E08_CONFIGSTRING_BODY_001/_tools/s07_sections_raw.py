import struct, json
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
d=open(P,"rb").read()
assert d[:2]==b"MZ"
e_lfanew,=struct.unpack_from("<I",d,0x3C)
print("e_lfanew=0x%X sig=%r" % (e_lfanew, d[e_lfanew:e_lfanew+4]))
coff=e_lfanew+4
nsec,=struct.unpack_from("<H",d,coff+2)
optsz,=struct.unpack_from("<H",d,coff+16)
opt=coff+20
magic,=struct.unpack_from("<H",d,opt)
print("NumberOfSections=%d SizeOfOptionalHeader=0x%X magic=0x%X" % (nsec,optsz,magic))
so=opt+optsz
print()
print("%-9s %-10s %-10s %-10s %-10s %-10s" % ("name","VSize","VAddr","RawSize","RawPtr","Chars"))
secs=[]
for i in range(nsec):
    b=so+i*40
    nm=d[b:b+8].rstrip(b"\0").decode("latin1")
    vs,va,rs,rp=struct.unpack_from("<IIII",d,b+8)
    ch,=struct.unpack_from("<I",d,b+36)
    secs.append((nm,va,vs,rp,rs,ch))
    print("%-9s 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X" % (nm,vs,va,rs,rp,ch))
print()
def which(rva):
    for nm,va,vs,rp,rs,ch in secs:
        if va<=rva<va+vs:
            inraw = rp<= (rp+(rva-va)) < rp+rs if rs else False
            return "%s (off 0x%X, in raw=%s)" % (nm, rp+(rva-va) if rs else -1, inraw)
    return "NOT MAPPED"
print("=== where do the server's call targets really live? ===")
for rva in (0x74E900,0x7656A0,0x765740,0x7572E0,0x7655E0,0x7655D8,0x499551,0x499566,0x499590,0x499651,0x4A0400,0xA0468,0xA0807,0xA0997):
    print("  RVA 0x%-7X -> %s" % (rva, which(rva)))
print()
sym=json.load(open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json",encoding="utf-8"))
want={0x74E900:"?",0x7656A0:"?",0x765740:"?",0x7572E0:"?",0x499551:"?",0x4A0400:"?"}
hits={}
for s in sym["symbols"]:
    r=s.get("rva")
    if isinstance(r,int) and r in want: hits.setdefault(r,[]).append((s["name"],s.get("section"),s.get("value")))
print("=== symbols exactly at those RVAs ===")
for r in want:
    print("  0x%X : %s" % (r, hits.get(r,"(none)")))
print()
print("=== symbols whose rva is in 0x74E000-0x74F000 ===")
c=0
for s in sym["symbols"]:
    r=s.get("rva")
    if isinstance(r,int) and 0x74E000<=r<0x74F000:
        print("  0x%X %-40s section=%s value=0x%X" % (r,s["name"],s.get("section"),s.get("value",0))); c+=1
        if c>=15: break
print()
print("=== symbol section histogram ===")
import collections
h=collections.Counter(s.get("section") for s in sym["symbols"])
print(dict(h))