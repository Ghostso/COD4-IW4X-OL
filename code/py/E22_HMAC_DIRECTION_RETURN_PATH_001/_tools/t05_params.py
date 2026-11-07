import sys,pefile,struct,io
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
OUT=open(r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_data\out_params.txt","w",encoding="utf-8")
def pr(x):OUT.write(x+"\n")
pe=pefile.PE(P,fast_load=True);IB=pe.OPTIONAL_HEADER.ImageBase;d=open(P,'rb').read();md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
secs=[(s.Name.rstrip(b'\0').decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def off(r):
 for n,va,vs,rp,rs in secs:
  if va<=r<va+vs:return rp+r-va if rs and r-va<rs else None
def show(a,b,tag):
 pr("="*74);pr(tag+" "+hex(a)+" "+hex(b));o=off(a)
 if o is None:pr("NO_RAW");return
 for ins in md.disasm(d[o:o+b-a],IB+a):
  pr("%06X %-22s %-34s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic+" "+ins.op_str))
show(0x6AC0C0,0x6AC3D0,"0x6AC0C0 full")
show(0x6AAE70,0x6AB180,"0x6AAE70 full")
show(0x6AC3D0,0x6AC5A0,"0x6AC3D0 caller")
# locate instruction refs to fields c8/ac/b0/5cc in 6ac0c0
pr("FIELD REFS")
o=off(0x6AC0C0)
for ins in md.disasm(d[o:o+0x310],IB+0x6AC0C0):
 s=ins.op_str.lower()
 if any(x in s for x in ("0xc8","0xac","0xb0","0x5cc","0x9c")):pr("%06X %s %s"%(ins.address-IB,ins.mnemonic,ins.op_str))

OUT.close()
