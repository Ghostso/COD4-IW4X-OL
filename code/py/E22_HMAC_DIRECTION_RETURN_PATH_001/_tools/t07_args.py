import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True);IB=pe.OPTIONAL_HEADER.ImageBase;d=open(P,'rb').read();md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def off(r):
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+s.Misc_VirtualSize:
   return s.PointerToRawData+r-s.VirtualAddress if s.SizeOfRawData and r-s.VirtualAddress<s.SizeOfRawData else None
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_data\out_args.txt","w",encoding="utf-8")
def show(a,b,tag):
 OUT.write("="*72+"\n"+tag+" "+hex(a)+" "+hex(b)+"\n")
 o=off(a)
 if o is None:OUT.write("NO_RAW\n");return
 for ins in md.disasm(d[o:o+b-a],IB+a):OUT.write("%06X %-20s %s\n"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
show(0x6AC0C0,0x6AC3D0,"6AC0C0")
show(0x6AAE70,0x6AAFFD,"6AAE70 head")
show(0x6AB0E0,0x6AB180,"HMAC compare")
OUT.close()
print("ok")
