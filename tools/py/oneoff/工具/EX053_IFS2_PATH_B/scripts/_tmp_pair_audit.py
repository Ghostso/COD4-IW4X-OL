from pathlib import Path
import csv,struct,hashlib
from capstone import *
IB=0x400000
D=Path('codoMP_client_shipRetail.exe').read_bytes()
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; o=pe+24; oh=struct.unpack_from('<H',D,pe+20)[0]; so=o+oh
S=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); S.append((i,nm,vs,va,rs,pr))
def sec(r):
 return next((x for x in S if x[3]<=r<x[3]+max(x[2],x[4])),None)
def off(r):
 s=sec(r); return None if not s or r-s[3]>=s[4] else s[5]+r-s[3]
def u32(r):
 q=off(r); return None if q is None else struct.unpack_from('<I',D,q)[0]
def isexec(r):
 s=sec(r); return bool(s and s[1]!='.tvm0' and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# exact raw refs
refs=[]
for i,nm,vs,va,rs,pr in S:
 if nm=='.tvm0': continue
 b=D[pr:pr+rs]
 for j in range(len(b)-6):
  if b[j]==0xff and b[j+1] in (0x15,0x25):
   sl=struct.unpack_from('<I',b,j+2)[0]
   if sl in (0xca8114,0xca8194,0xca812c,0xca819c,0xca8164): refs.append((va+j,sl,b[j+1]))
refs.sort()
# exact reference at 0xAA17B and 0xAA192; disassemble from known E8 target 0xAA17D? check bytes and preceding.
for r in (0xaa17b,0xaa192,0xb2d95,0xb2dac):
 print('---',hex(r),'---')
 for st in range(r-32,r+1):
  ins=list(md.disasm(D[off(st):off(r)+16],IB+st))
  hit=any(x.address-IB==r and x.size==6 and x.bytes[:2]==b'\xff\x15' for x in ins)
  if hit:
   print('start',hex(st),'ins',[(hex(x.address-IB),x.bytes.hex(),x.mnemonic+' '+x.op_str) for x in ins[:10]])
# inspect 0xAA17D as precise sequence
for st in (0xaa12a,0xaa17d):
 print('DIS',hex(st)); [print(hex(x.address-IB),x.bytes.hex(),x.mnemonic,x.op_str) for x in md.disasm(D[off(st):off(st)+160],IB+st)]
