import pefile
from capstone import *
p=r"COD OL\GDPLoader.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase; d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# IAT 名
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        if f.name: iat[f.address]=f.name.decode()
def dis(a,ln,label):
    o=pe.get_offset_from_rva(a-ib)
    print("==== %s 0x%08X ===="%(label,a))
    c=0
    for ins in md.disasm(d[o:o+ln], a):
        extra=""
        if "dword ptr [0x" in ins.op_str:
            try:
                tgt=int(ins.op_str.split("[")[1].split("]")[0],16)
                if tgt in iat: extra="  ; "+iat[tgt]
            except: pass
        print("  %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,extra)); c+=1
        if c>68: break
dis(0x10019920, 0xC0, "InitGdp: tqos 引用处")
print()
print("=== WINHTTP 导入槽 ===")
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    if imp.dll.decode().lower().startswith("winhttp"):
        for f in imp.imports:
            print("   0x%08X  %s"%(f.address, f.name.decode() if f.name else "ord"))
