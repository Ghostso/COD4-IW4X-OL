import pefile
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p)
ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
def off(rva): return pe.get_offset_from_rva(rva)
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
# find code refs to key strings: pipe prefix, ShareState_MMF, HostPid, mode iipslaunch
targets={}
for s in [b"\\\\.\\Pipe\\", b"Global\\IIPSShareState_MMF_", b"Global\\IIPSShareState_Mutex_",
          b"/mode iipslaunch", b"IIPSHostApp.exe", b"HostPid", b"IIPSClient.ini", b"iips.ini"]:
    i=d.find(s)
    if i>=0:
        rva=pe.get_rva_from_offset(i)
        targets[s]=ib+rva
        print("%-32r file=0x%06X rva=0x%06X va=0x%08X" % (s,i,rva,ib+rva))
print()
# scan .text for push imm32 equal to those VAs
text=[s for s in pe.sections if b".text" in s.Name][0]
base=text.PointerToRawData; size=text.SizeOfRawData
blob=d[base:base+size]
code_va=ib+text.VirtualAddress
want=set(targets.values())
for i in md.disasm(blob, code_va):
    if i.mnemonic in ("push","mov","lea","movzx") and i.op_str:
        for v in want:
            if ("0x%x"%v) in i.op_str:
                print("  %08X  %-28s %s   -> %s" % (i.address, i.bytes.hex(), i.mnemonic+" "+i.op_str,
                      [k.decode() for k,val in targets.items() if val==v][0]))
