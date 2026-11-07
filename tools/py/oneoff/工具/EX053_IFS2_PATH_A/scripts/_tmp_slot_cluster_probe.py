import struct,collections
from capstone import *
d=open(r"codoMP_client_shipRetail.exe","rb").read(); IB=0x400000
sh=struct.unpack_from("<I",d,0x3c)[0]; n=struct.unpack_from("<H",d,sh+6)[0]; opt=sh+24; oh=struct.unpack_from("<H",d,sh+20)[0]; o=opt+oh
secs=[]
for i in range(n):
 h=o+40*i; name=d[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",d,h+8); secs.append((i,name,va,vs,rs,pr))
def sec(rva):
 for x in secs:
  if x[2]<=rva<x[2]+min(x[3],x[4]):return x
 return None
def off(rva):
 x=sec(rva);return None if x is None else x[5]+rva-x[2]
def rd32(rva):
 f=off(rva);return None if f is None or f+4>len(d) else struct.unpack_from("<I",d,f)[0]
slots=[0xca8114,0xca8194,0xca812c,0xca819c,0xca8164]
md=Cs(CS_ARCH_X86,CS_MODE_32)
refs=collections.defaultdict(list)
for i,name,va,vs,rs,pr in secs:
 if name.lower()==".tvm0":continue
 b=d[pr:pr+min(vs,rs)]
 for j in range(len(b)-6):
  if b[j]==0xff and b[j+1] in (0x15,0x25):
   op=struct.unpack_from("<I",b,j+2)[0]
   if op in slots:refs[op].append(va+j)
for slot in slots:
 print("=== slot",hex(slot),"value",hex(rd32(slot-IB)),"refs",len(refs[slot]))
 for rva in refs[slot][:12]:
  f=off(rva); ins=next(md.disasm(d[f:f+15],IB+rva,count=1),None)
  before=d[max(0,f-64):f]; after=d[f+6:min(len(d),f+70)]
  print("CALL %08X self=%s bytes=%s"%(rva,ins.bytes.hex() if ins else "NO",ins.op_str if ins else ""))
  print(" before64",before.hex(" "))
  print(" after64 ",after.hex(" "))
