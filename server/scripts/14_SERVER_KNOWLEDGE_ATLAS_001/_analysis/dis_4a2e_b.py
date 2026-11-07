import pefile
from capstone import *
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(p,"rb").read()
pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
S={s.Name.rstrip(b"\x00").decode():(s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections}
va,vs,rp,rs=S[".text"]
md=Cs(CS_ARCH_X86, CS_MODE_32)
lo,hi=0x4A2E00,0x4A2FA0
seg=data[rp+(lo-va):rp+(hi-va)]
for ins in md.disasm(seg, lo):
    if ins.address>=hi: break
    print("  %08X  %-12s %s" % (ins.address, ins.mnemonic, ins.op_str))