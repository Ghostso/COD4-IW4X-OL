import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S=[]
for s in pe.sections:
    S.append((s.Name.rstrip(b"\x00").decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
Smap={x[0]:x[1:] for x in S}
def rva2off(rva):
    for nm,v,vs,rp,rs in S:
        if v<=rva<v+min(vs,rs): return rp+(rva-v)
    return None
TARGET_VA=IB+0xA2E50
print("=== 1) complete rel32 E8/E9 scan ===")
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]
    code=data[rp:rp+rs]; base=IB+va
    calls=[];jmps=[]
    for i in range(len(code)-5):
        b=code[i]
        if b in (0xE8,0xE9):
            disp=struct.unpack_from("<i",code,i+1)[0]
            t=base+i+5+disp
            if t==TARGET_VA:
                (calls if b==0xE8 else jmps).append(base+i)
    print(" %-6s E8=%d E9=%d %s" % (nm,len(calls),len(jmps),[hex(x) for x in (calls+jmps)[:10]]))
print()
print("=== 2) VA 0x%X pointer occurrences ===" % TARGET_VA)
locs=[]; o=0; pat=struct.pack("<I",TARGET_VA)
while True:
    i=data.find(pat,o)
    if i<0: break
    locs.append(i); o=i+1
print(" total=",len(locs))
print()
print("=== 3) .rimp classification ===")
rv,rvv,rr,rrs=Smap[".rimp"]
rimp=data[rr:rr+rrs]
c={"rimp":0,"text":0,"rdata":0,"img":0,"non":0}
for i in range(0,len(rimp)-4,4):
    v=struct.unpack_from("<I",rimp,i)[0]
    if 0xDC11000<=v<0xDC14000: c["rimp"]+=1
    elif 0x1000<=v<0x7AE000: c["text"]+=1
    elif 0x7AE000<=v<0x8F1000: c["rdata"]+=1
    elif 0x400000<=v<0x400000+pe.OPTIONAL_HEADER.SizeOfImage: c["img"]+=1
    else: c["non"]+=1
print(" ", c, " (values stored as image-relative VA minus ImageBase? testing)")
# try treating values as RVA
c2={"rimp_rva":0,"text":0,"rdata":0,"data":0,"non":0}
for i in range(0,len(rimp)-4,4):
    v=struct.unpack_from("<I",rimp,i)[0]
    if 0xC11000<=v<0xC14000: c2["rimp_rva"]+=1
    elif 0x1000<=v<0x7AE000: c2["text"]+=1
    elif 0x7AE000<=v<0x8F1000: c2["rdata"]+=1
    elif 0x8F1000<=v<0xD94E000: c2["data"]+=1
    else: c2["non"]+=1
print(" as-RVA:", c2)