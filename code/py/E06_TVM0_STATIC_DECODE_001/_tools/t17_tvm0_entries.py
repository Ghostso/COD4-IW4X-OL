import pefile, struct
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
rec=open(REC,"rb").read(); pe=pefile.PE(REC,fast_load=True); IB=0x400000
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
tv,_,tr,ts=S[".text"]; text=rec[tr:tr+ts]
# collect all .text rel32 targets into .tvm0
tg=set(); cnt=0
for i in range(len(text)-5):
    if text[i] in (0xE8,0xE9):
        disp=struct.unpack_from("<i",text,i+1)[0]
        dest=tv+i+5+disp
        if 0xD958000<=dest<0xDC11000: tg.add(dest); cnt+=1
print("distinct .tvm0 entry targets referenced from .text: %d (branches=%d)" % (len(tg),cnt))
# Verify prologues at those targets, using a BSS-free heuristic: 55 8B EC / 53 / 51 / 56 / 57 / 83 EC / 81 EC
def proff(r):
    for nm,(v,vs,rp,rs) in S.items():
        if v<=r<v+min(vs,rs): return rp+(r-v)
ok=0; pats={}
for t in tg:
    o=proff(t)
    if o is None: continue
    b=rec[o:o+4]
    if b[:3]==b"\x55\x8b\xec" or b[:1]==b"\x55" or b[:1]==b"\x53" or b[:1]==b"\x56" or b[:1]==b"\x57" or b[:2]==b"\x83\xec" or b[:2]==b"\x81\xec" or b[:2]==b"\x8b\xff":
        ok+=1
    pats[b[:2].hex()]=pats.get(b[:2].hex(),0)+1
print("targets whose first bytes look like a function prologue: %d / %d (%.1f%%)" % (ok,len(tg),100.0*ok/max(1,len(tg))))
print("top first-2-byte patterns at targets:", sorted(pats.items(), key=lambda x:-x[1])[:12])