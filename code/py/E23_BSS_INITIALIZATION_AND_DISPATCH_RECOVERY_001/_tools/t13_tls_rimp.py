import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
print("TLS directory present:", hasattr(pe,"DIRECTORY_ENTRY_TLS"))
if hasattr(pe,"DIRECTORY_ENTRY_TLS"):
    t=pe.DIRECTORY_ENTRY_TLS.struct
    for f in ("StartAddressOfRawData","EndAddressOfRawData","AddressOfIndex","AddressOfCallBacks","SizeOfZeroFill","Characteristics"):
        v=getattr(t,f); print("  %s = 0x%08X"%(f,v))
    print("  Callbacks (VAs):",[hex(c) for c in (pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks and [] or [])])
# read callback array
cb=pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks
if cb:
    r=cb-IB
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
            o=s.PointerToRawData+r-s.VirtualAddress
            if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData:
                arr=[]
                for i in range(0,0x20,4):
                    v=struct.unpack_from("<I",d,o+i)[0]; arr.append(v)
                    if v==0: break
                print("  callback array:",[hex(x) for x in arr]); print("  sec of cb array:", s.Name)
            break
# .rimp raw
s=[x for x in pe.sections if x.Name.startswith(b".rimp")][0]
print("\n== .rimp ==  VA %08X VS %08X RAW %08X RS %08X"%(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData))
blob=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
print("first 128 bytes:",blob[:128].hex())
# nonzero ratio & first dwords
nz=sum(1 for b in blob if b)
print("nonzero bytes:",nz,"of",len(blob))
print("first 16 dwords:",[hex(struct.unpack_from("<I",blob,i)[0]) for i in range(0,64,4)])
