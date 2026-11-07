import sys,pefile,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True);d=open(P,'rb').read();IB=pe.OPTIONAL_HEADER.ImageBase
text=pe.sections[0]; base=text.VirtualAddress; data=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
def calls(t):
 tv=(IB+t)&0xffffffff; out=[]
 for i in range(len(data)-5):
  if data[i] in (0xe8,0xe9):
   rel=struct.unpack_from('<i',data,i+1)[0]
   if ((IB+base+i+5+rel)&0xffffffff)==tv: out.append(base+i)
 return out
for t in (0x6ABE80,0x6AC0C0,0x6AC3D0,0x6AAE70,0x6ABBC0):
 print(hex(t),[hex(x) for x in calls(t)])
# special: callers of 0x6AC3D0 via rel scan
# function boundaries around 0x6AC3D0
def off(rva):
 for s in pe.sections:
  va=s.VirtualAddress; rs=s.SizeOfRawData; rp=s.PointerToRawData
  if va<=rva<va+s.Misc_VirtualSize:
   return rp+rva-va if rs and rva-va<rs else None
from capstone import *
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
o=off(0x6AC3D0)
for ins in md.disasm(d[o:o+0x250],IB+0x6AC3D0):
 print("%06X %-20s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
