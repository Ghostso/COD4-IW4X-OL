import struct, pefile
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def sec(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return n
def off(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return rp+r-va if rs and r-va<rs else None
def rd(rva,n):
    o=off(rva); return d[o:o+n] if o is not None else None
tls=pe.OPTIONAL_HEADER.DATA_DIRECTORY[9]
print("TLS dir RVA %08X size %08X sec=%s"%(tls.VirtualAddress,tls.Size,sec(tls.VirtualAddress)))
b=rd(tls.VirtualAddress,24)
vals=struct.unpack_from("<6I",b,0)
names=["StartAddressOfRawData","EndAddressOfRawData","AddressOfIndex","AddressOfCallBacks","SizeOfZeroFill","Characteristics"]
for nm,v in zip(names,vals):
    tag=""
    if nm.startswith("Address") and (v>>24)==0 and v>IB:
        tag=" (RVA %06X sec=%s)"%(v-IB,sec(v-IB))
    print("  %-22s %08X%s"%(nm,v,tag))
cb=vals[3]
if cb>IB:
    r=cb-IB
    o=off(r)
    print("callback array at VA %08X RVA %06X sec=%s"%(cb,r,sec(r)))
    arr=[]
    for i in range(0,64,4):
        v=struct.unpack_from("<I",d,o+i)[0]; arr.append(v)
        if v==0: break
    print("  callbacks:",[hex(x) for x in arr])
    for v in arr:
        if v: print("    cb VA %08X RVA %06X sec=%s"%(v,v-IB,sec(v-IB)))
# .rimp
s=[x for x in secs if x[0]==".rimp"][0]
n,va,vs,rp,rs=s
blob=d[rp:rp+rs]
print("\n== .rimp VA %08X VS %08X RAW %08X RS %08X sec(%08X)=%s =="%(va,vs,rp,rs,va,None))
# does .rimp contain our vtables/targets?
import struct as st
for label,val in [("0xC5A31C",0xC5A31C),("0xC5B0A4",0xC5B0A4),("0xA87D50",0xA87D50),("0xA878A0",0xA878A0),("0xA85AD0",0xA85AD0),("0xAAAE70",0xAAAE70)]:
    pat=st.pack("<I",val)
    print("  %s occurrences in .rimp: %d"%(label, blob.count(pat)))
print("  .rimp nonzero bytes: %d / %d"%(sum(1 for x in blob if x),len(blob)))
# try to interpret as (va, target) pairs; scan for plausible VA-looking dwords
dws=[st.unpack_from("<I",blob,i)[0] for i in range(0,len(blob),4)]
plaus=[ (i,hex(w)) for i,w in enumerate(dws) if 0x400000<=w<0xE000000 ]
print("  plausible VA-like dwords in .rimp:",len(plaus))
print("  first 40:",plaus[:40])
