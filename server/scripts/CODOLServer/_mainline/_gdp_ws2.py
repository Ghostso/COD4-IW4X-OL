import pefile, re
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
print("=== GDPLoader 全部 WS2/KERNEL 网络类导入槽 ===")
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    nm=imp.dll.decode()
    if nm.lower() not in ("ws2_32.dll","kernel32.dll","winhttp.dll"): continue
    for f in imp.imports:
        n=f.name.decode() if f.name else "ord"
        if any(k in n for k in ("gethost","GetAddr","socket","connect","send","recv","bind","listen","getserv","WSA")):
            print("   %s  0x%08X  %s"%(nm, f.address, n))
