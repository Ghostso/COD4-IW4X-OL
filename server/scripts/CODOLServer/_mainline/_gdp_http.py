import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
import re
strs={}
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    if nm not in (".rdata",".data"): continue
    seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    for m in re.finditer(rb"[\x20-\x7e]{4,}", seg):
        strs[ib+s.VirtualAddress+m.start()]=m.group().decode("latin1")
def hint(ops):
    for v,txt in strs.items():
        if ("0x%x"%v) in ops: return "  ; \""+txt[:70]+"\""
    if "dword ptr [0x" in ops:
        try:
            t=int(ops.split("[")[1].split("]")[0],16)
            if t in iat: return "  ; "+iat[t]
        except: pass
    return ""
# 找 WinHttp 调用点
print("=== GDPLoader 内所有 WinHttp / WSA 调用 ===")
for s in pe.sections:
    seg=d[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
    va=ib+s.VirtualAddress
    for ins in md.disasm(seg, va):
        o=ins.op_str
        if "dword ptr [0x" in o:
            try: t=int(o.split("[")[1].split("]")[0],16)
            except: continue
            if t in iat and any(k in iat[t] for k in ("WinHttp","WSA","gethostbyname","socket","connect","send","recv","GetAddr")):
                print("   %08X  %-22s %s %s  ; %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,iat[t]))
