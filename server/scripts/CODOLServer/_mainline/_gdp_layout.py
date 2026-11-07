import pefile, os, math, collections
from capstone import *
for f in ["GDPLoader.dll","GameDataPlatformServer.dll","GDPImpl.dll","GDPCODOTrail.dll"]:
    p=os.path.join("COD OL",f)
    if not os.path.isfile(p): print("MISSING",f); continue
    pe=pefile.PE(p); d=open(p,"rb").read()
    print("="*64); print("%s  %d B  IB=0x%X  EP=0x%X  machine=%s"%(f,len(d),pe.OPTIONAL_HEADER.ImageBase,pe.OPTIONAL_HEADER.AddressOfEntryPoint,hex(pe.FILE_HEADER.Machine)))
    for s in pe.sections:
        nm=s.Name.rstrip(b"\x00").decode("latin1")
        seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData][:0x20000]
        if seg:
            c=collections.Counter(seg); tot=len(seg)
            ent=-sum((v/tot)*math.log2(v/tot) for v in c.values())
        else: ent=0
        print("   %-10s VA 0x%06X vsize 0x%-8X ent %.2f"%(nm,s.VirtualAddress,s.Misc_VirtualSize,ent))
    # entry disasm
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    va=pe.OPTIONAL_HEADER.ImageBase+pe.OPTIONAL_HEADER.AddressOfEntryPoint
    o=pe.get_offset_from_rva(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    print("   --- entry disasm ---")
    n=0
    for ins in md.disasm(d[o:o+30], va):
        print("      %08X  %-18s %s %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str)); n+=1
        if n>=6: break
