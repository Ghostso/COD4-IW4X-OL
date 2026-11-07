import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True);IB=pe.OPTIONAL_HEADER.ImageBase;d=open(P,'rb').read();md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def off(r):
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
   return s.PointerToRawData+r-s.VirtualAddress if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData else None
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_data\out_callers_args.txt","w",encoding="utf-8")
def show(a,b,tag):
 OUT.write("="*72+"\n"+tag+" "+hex(a)+"\n");o=off(a)
 if o is None:OUT.write("NO_RAW\n");return
 for ins in md.disasm(d[o:o+b-a],IB+a):OUT.write("%06X %-20s %s\n"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
# callers of 6AC3D0
show(0x68EEB0,0x68EF20,"caller1 68EEB0")
show(0x68EFF0,0x68F060,"caller2 68EFF0")
# caller of 6AC3D0 via jmp 6AC0C0 - stack args likely this+8
OUT.close();print("ok")
