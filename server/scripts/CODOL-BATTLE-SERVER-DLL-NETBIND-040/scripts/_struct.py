import pefile,struct,json,collections,math,io
DLL=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False);IB=pe.OPTIONAL_HEADER.ImageBase
out={}
out["image_base"]=hex(IB); out["size_of_image"]=hex(pe.OPTIONAL_HEADER.SizeOfImage)
out["entry_point"]=hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
dd=[]
for i,d in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
    if d.VirtualAddress or d.Size: dd.append((i,hex(d.VirtualAddress),hex(d.Size)))
out["data_dirs"]=dd
secs=[]
for s in pe.sections:
    data=b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    cnt=collections.Counter(data)
    ent=-sum((c/len(data))*math.log2(c/len(data)) for c in cnt.values()) if data else 0
    secs.append(dict(name=s.Name.rstrip(b"\0").decode("latin1"),va=hex(s.VirtualAddress),
        vsize=hex(s.Misc_VirtualSize),raw=hex(s.PointerToRawData),rsize=hex(s.SizeOfRawData),
        chars=hex(s.Characteristics),entropy=round(ent,3)))
out["sections"]=secs
# relocations
if hasattr(pe,"DIRECTORY_ENTRY_BASERELOC"):
    c=collections.Counter();n=0;blocks=len(pe.DIRECTORY_ENTRY_BASERELOC);inrange=0
    idata=0
    for rb in pe.DIRECTORY_ENTRY_BASERELOC:
        for e in rb.entries:
            t=e.type if hasattr(e,"type") else (e.data>>12)
            rv=(e.rva if hasattr(e,"rva") else (e.data & 0xfff))
            c[t]+=1;n+=1
            r=rb.struct.VirtualAddress+rv
            if 0xb02000<=r<0xb06f00: idata+=1
    out["reloc"]=dict(blocks=blocks,entries=n,types={str(k):v for k,v in c.items()},in_idata2=idata)
# exports
if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
    ex=[]
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        ex.append(dict(ordinal=e.ordinal,name=(e.name.decode() if e.name else None),rva=hex(e.address)))
    out["exports"]=ex
# imports (regular)
imp=[]
for ent in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    imp.append(dict(dll=ent.dll.decode(),count=len(ent.imports)))
out["regular_imports"]=imp
print(json.dumps(out,indent=2))
io.open(r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040\evidence\pe_structure.json","w",encoding="utf-8").write(json.dumps(out,indent=2,ensure_ascii=False))
