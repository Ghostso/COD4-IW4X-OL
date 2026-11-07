import sys,pefile,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E22_HMAC_DIRECTION_RETURN_PATH_001\_tools")
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True);IB=pe.OPTIONAL_HEADER.ImageBase;d=open(P,'rb').read();md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
secs=[(s.Name.rstrip(b'\0').decode(),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def sec(r):
 for x in secs:
  if x[1]<=r<x[1]+x[2]:return x
def off(r):
 x=sec(r)
 if not x:return None
 n,va,vs,rp,rs=x
 return rp+r-va if rs and r-va<rs else None
def show(a,b,tag):
 print("="*72);print(tag,hex(a),hex(b));o=off(a)
 if o is None:print("NO_RAW",sec(a));return
 for ins in md.disasm(d[o:o+b-a],IB+a):print("%06X %-24s %s %s"%(ins.address-IB,bytes(ins.bytes).hex(),ins.mnemonic,ins.op_str))
# Function boundaries via find end
show(0x6A5BE0,0x6A5D80,"0x6A5BE0 (call target of 0xA85BE0?)")
show(0x6A8BF0,0x6A8D80,"0x6A8BF0 (helper in HMAC path)")
show(0x6A81F0,0x6A83A0,"0x6A81F0 (helper)")
show(0x6AA770,0x6AA8A0,"0x6AA770 (error state)")
# find all direct callers of 0x6AC0C0 and 0x6AAE70 from rel32 byte scan
text=pe.sections[0]; base=text.VirtualAddress; data=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
def calls(t):
 tv=(IB+t)&0xffffffff; out=[]
 for i in range(len(data)-5):
  if data[i] in (0xe8,0xe9):
   rel=struct.unpack_from('<i',data,i+1)[0];dst=(IB+base+i+5+rel)&0xffffffff
   if dst==tv:out.append(base+i)
 return out
for t in (0x6AC0C0,0x6AAE70,0x6A5BE0,0x6A8BF0,0x6A81F0):
 print("CALLERS",hex(t),[hex(x) for x in calls(t)])
