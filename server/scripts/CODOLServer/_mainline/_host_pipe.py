import pefile
from capstone import *
p=r"COD OL\IIPS\IIPSHost.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# imports via IAT
iat={}
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    for f in imp.imports:
        nm=f.name.decode() if f.name else "ord_%s"%f.ordinal
        iat.setdefault(nm, []).append(f.address)
for k in ("CreateNamedPipeA","ConnectNamedPipe","DisconnectNamedPipe","CreateMutexA","ReleaseMutex"):
    if k in iat: print("%-22s IAT %s"%(k, [hex(x) for x in iat[k]]))
print()
# xref pipe prefix string
i=d.find(b"\\\\.\\Pipe\\")
print("pipe prefix @ file 0x%06X va 0x%08X"%(i, ib+pe.get_rva_from_offset(i)))
text=[s for s in pe.sections if b".text" in s.Name][0]
blob=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
code_va=ib+text.VirtualAddress
want=set()
for k in ("CreateNamedPipeA","ConnectNamedPipe","DisconnectNamedPipe"):
    for a in iat.get(k,[]): want.add(a)
want.add(ib+pe.get_rva_from_offset(i))
names={}
for k in ("CreateNamedPipeA","ConnectNamedPipe","DisconnectNamedPipe"):
    for a in iat.get(k,[]): names[a]=k
names[ib+pe.get_rva_from_offset(i)]="\\\\\\\\.\\\\Pipe\\\\"
for ins in md.disasm(blob, code_va):
    if ins.op_str and "dword ptr [0x" in ins.op_str:
        try:
            tgt=int(ins.op_str.split("[")[1].split("]")[0],16)
        except: continue
        if tgt in names and ins.mnemonic in ("call","jmp","push","mov"):
            print("  %08X  %-22s %s %s   ; %s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,names[tgt]))
