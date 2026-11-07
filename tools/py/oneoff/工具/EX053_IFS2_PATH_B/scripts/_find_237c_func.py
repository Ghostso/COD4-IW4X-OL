import pathlib,struct,collections,bisect
from capstone import *
from capstone.x86 import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes();IB=0x400000
SEC=[(0,0x1000,0x8A689A,0x1000,0x593000,0x60000020),(1,0x8A8000,0x16DA70,0x594000,0x16E000,0x40000040),(2,0xA16000,0xDBB1CC0,0x702000,0x62000,0xC0000040),(3,0xE5C8000,0x31,0x764000,0x1000,0xC0000040),(4,0xE5C9000,0x9228,0x765000,0xA000,0x40000040),(5,0xE5D3000,0x4000,0x76F000,0x2000,0x60000020),(6,0xE5D7000,0x82000,0x771000,0x6000,0xE0000020)]
def sec(r):
 for s in SEC:
  if s[1]<=r<s[1]+max(s[2],s[4]):return s
 return None
def r2o(r):
 s=sec(r)
 if not s:return None
 x=r-s[1];return s[3]+x if 0<=x<s[4] else None
def ex(r):
 s=sec(r);return bool(s and s[5]&0x20000000)
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# collect direct rel32 branch/call targets across executable sections
targets=collections.Counter()
for _,v,vs,rp,rs,ch in SEC:
 if not ch&0x20000000:continue
 b=D[rp:rp+rs]
 for k in range(len(b)-5):
  op=b[k]
  if op in (0xE8,0xE9):t=v+k+5+struct.unpack_from('<i',b,k+1)[0]
  elif 0x70<=op<=0x7f or op==0xeb:t=v+k+2+struct.unpack_from('<b',b,k+1)[0]
  else:continue
  if ex(t):targets[t]+=1
print('targets',len(targets))
# A function candidate which starts before 237c44 and has a direct target/call.
cands=sorted({t for t in targets if t<=0x237C44 and t>=0x237C15-0x200})
for a in cands[-30:]:
 print('\nCAND',hex(a),'hits',targets[a])
 for ins in md.disasm(D[r2o(a):r2o(a)+96],IB+a):
  print('%08X %-18s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=IB+a+72:break
