import struct,collections
from capstone import *
d=open(r'codoMP_client_shipRetail.exe','rb').read(); ib=0x400000
sh=struct.unpack_from('<I',d,0x3c)[0]; n=struct.unpack_from('<H',d,sh+6)[0]; opt=sh+24; o=opt+struct.unpack_from('<H',d,sh+20)[0]
secs=[]
for i in range(n):
 h=o+40*i; t=d[h:h+8].split(b'\x00')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',d,h+8); secs.append((t,va,vs,rs,pr))
def off(rva):
 for t,va,vs,rs,pr in secs:
  if va<=rva<va+min(vs,rs): return pr+rva-va
 raise ValueError(hex(rva))
f=off(0x8a8000)
print('=== suffix continuity from 0xCA876C ===')
for i in range(475,600):
 v=struct.unpack_from('<I',d,f+4*i)[0]; va=0xca8000+4*i
 print('%4d %08X %08X %s'%(i,va,v,'PTR' if ib<=v<ib+0xe659000 else 'ZERO' if v==0 else 'OTHER'))
 if i>=570: break
print('=== class runs 0xCA8000..0xCA9000 ===')
classes=[]
for i in range(0x1000//4):
 v=struct.unpack_from('<I',d,f+4*i)[0]; classes.append('P' if ib<=v<ib+0xe659000 else 'Z' if v==0 else 'S' if v>>28==8 else 'X')
start=0
for i in range(1,len(classes)+1):
 if i==len(classes) or classes[i]!=classes[start]:
  print(hex(0xca8000+4*start),hex(0xca8000+4*i),classes[start],i-start); start=i
print('=== disassembly 0x365E0.. ===')
md=Cs(CS_ARCH_X86,CS_MODE_32); fb=off(0x365e0); b=d[fb:off(0x367a0)]
for ins in md.disasm(b,ib+0x365e0):
 print('%08X %-9s %s'%(ins.address,ins.mnemonic,ins.op_str))
 if ins.address>=ib+0x366a5:break
print('=== direct E8 callers ===')
for target in [0x3667a,0x36691,0x366a8]:
 found=[]
 for t,va,vs,rs,pr in secs:
  if t.lower()=='.tvm0': continue
  raw=min(vs,rs); b=d[pr:pr+raw]
  for i in range(len(b)-4):
   if b[i]==0xe8 and i+5+struct.unpack_from('<i',b,i+1)[0]==target: found.append((t,va+i))
 print(hex(ib+target),len(found),found[:50])
