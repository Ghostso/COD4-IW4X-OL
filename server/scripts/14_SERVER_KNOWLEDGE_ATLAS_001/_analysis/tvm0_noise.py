import pefile, struct, collections
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
Smap={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
# Build set of "plausible function starts" = preceded by 0xCC padding OR 0xC3 ret
def func_starts(nm):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]
    st=set()
    for i in range(1,len(code)):
        if code[i-1] in (0xCC,0xC3) and code[i] not in (0xCC,0x00):
            st.add(va+i)
    return st
for nm in (".text",".tvm0"):
    va,vs,rp,rs=Smap[nm]; code=data[rp:rp+rs]; base=va
    e8=[i for i,b in enumerate(code) if b==0xE8]
    st=func_starts(nm)
    hits=0; tot=0
    for i in e8:
        if i+5>len(code): continue
        disp=struct.unpack_from("<i",code,i+1)[0]
        t=base+i+5+disp
        if va<=t<va+vs:
            tot+=1
            if t in st: hits+=1
    print("%-6s E8 bytes=%6d  in-image targets=%6d  landing on plausible func start=%6d (%.1f%%)"
          % (nm,len(e8),tot,hits,100.0*hits/max(1,tot)))
    print("       func-start set size = %d  (density %.1f%% of section)" % (len(st),100.0*len(st)/vs))
print()
# Is the .tvm0 hit at RVA 0xD9D940F plausible? show surrounding bytes and decode context
va,vs,rp,rs=Smap[".tvm0"]
off=rp+(0xD9D940F-va)
print("=== .tvm0 around RVA 0xD9D940F ===")
print("bytes:", data[off-16:off+20].hex(" "))
print()
# and the same for the F3-claimed byte-match site 0xD97BF7E
off2=rp+(0xD97BF7E-va)
print("=== .tvm0 around RVA 0xD97BF7E (F3 byte-match site) ===")
print("bytes:", data[off2-16:off2+20].hex(" "))