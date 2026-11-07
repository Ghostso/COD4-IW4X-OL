import struct, pefile
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={}
for s in pe.sections:
    S[s.Name.rstrip(b"\x00").decode()]=(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData)
# Count image-relative VA pointers stored in .rdata (as a baseline for "unfixed pointer tables")
va,vs,rp,rs=S[".rdata"]
rdata=data[rp:rp+rs]
lo,hi=IB,IB+pe.OPTIONAL_HEADER.SizeOfImage
n=0; samples=[]
for i in range(0,len(rdata)-4):
    v=struct.unpack_from("<I",rdata,i)[0]
    if lo<=v<hi:
        n+=1
        if len(samples)<12: samples.append("0x%X:0x%08X"%(rp+i,v))
print(".rdata size", len(rdata), "VA-like u32 occurrences:", n)
print("samples:", samples)
# how many of those point into .text?
def tgt(v):
    for nm,(v0,vs0,rp0,rs0) in S.items():
        if v0<=v<v0+max(vs0,0): return nm
    return None
t=0
for i in range(0,len(rdata)-4):
    v=struct.unpack_from("<I",rdata,i)[0]
    if tgt(v)==".text": t+=1
print(".rdata->.text pointer occurrences:", t)