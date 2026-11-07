import pefile, struct, collections
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={}
for s in pe.sections:
    S[s.Name.rstrip(b"\x00").decode()]=(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData)
rv,_,rr,rs=S[".rimp"]
rimp=data[rr:rr+rs]
def tgt(v):
    for nm,(va,vs,rp,rsz) in S.items():
        if va<=v<va+max(vs,rsz): return nm
    return None
cnt=collections.Counter()
for i in range(0,len(rimp)-4,4):
    v=struct.unpack_from("<I",rimp,i)[0]
    if 0x400000<=v<0x400000+pe.OPTIONAL_HEADER.SizeOfImage:
        cnt[tgt(v)]+=1
print("VA-like u32 in .rimp by target section:", dict(cnt))
# ascii strings in .rimp
strings=[]
cur=b""
for b in rimp:
    if 32<=b<127: cur+=bytes([b])
    else:
        if len(cur)>=4: strings.append(cur.decode())
        cur=b""
if len(cur)>=4: strings.append(cur.decode())
print("ascii strings (len>=4) count:", len(strings))
print("sample:", strings[:40])
# Does any .rimp value point into .text?
txt=[]
for i in range(0,len(rimp)-4,4):
    v=struct.unpack_from("<I",rimp,i)[0]
    t=tgt(v)
    if t==".text": txt.append((i,v))
print("pointers into .text:", len(txt))
for i,v in txt[:20]: print("   off 0x%X -> 0x%08X"%(i,v))