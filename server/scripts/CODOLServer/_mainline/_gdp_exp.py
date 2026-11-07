import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# 导出表
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
                                       pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
print("=== EXPORTS ===")
if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
    for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        print("   ord %-4s VA 0x%08X  %s"%(s.ordinal, ib+s.address, s.name.decode() if s.name else ""))
print()
print("=== IMPORTS ===")
if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
    for imp in pe.DIRECTORY_ENTRY_IMPORT:
        print("   %-28s %d"%(imp.dll.decode(), len(imp.imports)))
print()
# 找 "tqos.gamesafe.qq.com" 的引用
i=d.find(b"tqos.gamesafe.qq.com")
va=ib+pe.get_rva_from_offset(i)
print("tqos.gamesafe.qq.com @ file 0x%06X VA 0x%08X"%(i,va))
le=va.to_bytes(4,"little")
hits=[]; s=0
while True:
    j=d.find(le,s)
    if j<0: break
    hits.append(j); s=j+1
print("引用点:", [hex(ib+pe.get_rva_from_offset(h)) for h in hits])
