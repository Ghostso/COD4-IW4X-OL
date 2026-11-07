import pefile, struct, collections
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S=[]; 
for s in pe.sections:
    S.append((s.Name.rstrip(b"\x00").decode(), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
Smap={x[0]:x[1:] for x in S}
rv,rvv,rr,rrs=Smap[".rimp"]
rimp=data[rr:rr+rrs]
vals=[]
for i in range(0,len(rimp)-3,4):
    vals.append((i,struct.unpack_from("<I",rimp,i)[0]))
# text-referencing values
tv=[(o,v) for o,v in vals if 0x1000<=v<0x7AE000]
print("RVA values pointing into .text:", len(tv))
print("min=0x%X max=0x%X" % (min(v for _,v in tv), max(v for _,v in tv)))
print("first 25:", ["0x%X"%v for _,v in tv[:25]])
print()
near=[(o,v) for o,v in tv if 0xA0000<=v<0xA5000]
print("into .text near 0xA0000..0xA5000:", len(near), ["0x%X"%v for _,v in near])
n2=[(o,v) for o,v in tv if 0xA2E00<=v<0xA2F00]
print("into .text near 0xA2E00..0xA2F00:", len(n2), ["0x%X"%v for _,v in n2])
print()
print("=== .rimp layout probe: stride guess ===")
for stride in (8,12,16):
    ok=0; tot=0
    for i in range(0,len(rimp)-stride,stride):
        tot+=1
        a=struct.unpack_from("<I",rimp,i)[0]
        b=struct.unpack_from("<I",rimp,i+stride//2)[0]
        if 0x1000<=a<0xDC14000: ok+=1
    print(" stride %2d: first-field-plausible %d/%d" % (stride, ok, tot))
print()
print("=== count of records where field0 is a plausible image RVA ===")
pl=sum(1 for o,v in vals if 0x1000<=v<0xDC14000)
print(" plausible RVA at 4-byte-aligned index: %d / %d (%.1f%%)" % (pl,len(vals),100.0*pl/len(vals)))