import pefile, struct
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
LAST0=0x0DC11000; LAST1=0x0DC11000+0x3214000
print("=== who references the LAST .tp3 VA range 0x%X..0x%X ? ===" % (IB+LAST0,IB+LAST1))
tv,_,tr,ts=S[".text"]; text=rec[tr:tr+ts]
c=0;sites=[]
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=tv+i+5+disp
        if LAST0<=dest<LAST1: c+=1; sites.append(tv+i)
print("  .text rel32 into last-.tp3 VA: %d  %s" % (c,[hex(x) for x in sites[:10]]))
u=0
for i in range(0,len(rec)-3,4):
    v=struct.unpack_from("<I",rec,i)[0]
    if IB+LAST0<=v<IB+LAST1: u+=1
print("  whole-image aligned u32 pointing into last-.tp3 VA: %d" % u)
print()
print("=== .rimp fixup table: what does it point at? ===")
rv,rvv,rr,rrs=S[".rimp"]
rimp=rec[rr:rr+rrs]
import collections
cls=collections.Counter()
for i in range(0,len(rimp)-3,4):
    v=struct.unpack_from("<I",rimp,i)[0]
    rva=v-IB
    if IB<=v<IB+pe.OPTIONAL_HEADER.SizeOfImage:
        for nm,(a,b,rp,rs) in S.items():
            if a<=rva<a+max(b,rs): cls[nm]+=1; break
        else: cls["?"]+=1
print("  .rimp u32 -> section:",dict(cls))
print("  any .rimp value pointing into last-.tp3 VA (0x%X..)? " % (IB+LAST0), sum(1 for i in range(0,len(rimp)-3,4) if IB+LAST0<=struct.unpack_from("<I",rimp,i)[0]<IB+LAST1))