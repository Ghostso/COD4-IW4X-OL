import pefile
from capstone import *
from capstone.x86 import *
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={}
for s in pe.sections:
    S[s.Name.rstrip(b"\x00").decode()]=(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData)
va,vs,rp,rs=S[".text"]
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
# find function boundaries via int3 padding + prologues around 0x4A2E00..0x4A3000
lo,hi=0x4A2D00,0x4A3200
seg=data[rp+(lo-va):rp+(hi-va)]
print("=== disassembly 0x%X..0x%X ===" % (lo,hi))
cnt=0
for ins in md.disasm(seg, lo):
    if ins.address>=hi: break
    print("  %08X  %-12s %s" % (ins.address, ins.mnemonic, ins.op_str))
    cnt+=1
    if cnt>160: print("   ... truncated"); break