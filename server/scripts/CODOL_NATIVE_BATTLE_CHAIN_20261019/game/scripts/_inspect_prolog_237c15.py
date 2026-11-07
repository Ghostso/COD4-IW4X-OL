import pathlib,struct,collections,bisect
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
# Sections (va, vsize, raw, rawsize, chars)
SEC=[(0x1000,0x8A689A,0x1000,0x593000,0x60000020),(0x8A8000,0x16DA70,0x594000,0x16E000,0x40000040),(0xA16000,0xDBB1CC0,0x702000,0x62000,0xC0000040),(0xE5C8000,0x31,0x764000,0x1000,0xC0000040),(0xE5C9000,0x9228,0x765000,0xA000,0x40000040),(0xE5D3000,0x4000,0x76F000,0x2000,0x60000020),(0xE5D7000,0x82000,0x771000,0x6000,0xE0000020)]
def sec(r):
 for i,(v,vs,rp,rs,ch) in enumerate(SEC):
  if v<=r<v+max(vs,rs): return i,v,vs,rp,rs,ch
 return None
def r2o(r):
 s=sec(r)
 if not s:return None
 i,v,vs,rp,rs,ch=s; x=r-v
 return rp+x if 0<=x<rs else None
def o2r(o):
 for i,(v,vs,rp,rs,ch) in enumerate(SEC):
  if rp<=o<rp+rs:return v+o-rp
# valid function starts by common prologues: push ebp; mov ebp,esp OR sub esp,imm OR mov edi,edi;push ebp
pro=[]
for i,(v,vs,rp,rs,ch) in enumerate(SEC):
 if not ch&0x20000000:continue
 b=D[rp:rp+rs]
 for k in range(len(b)-6):
  if b[k]==0x55 and b[k+1]==0x8B and b[k+2]==0xEC:
   if k==0 or b[k-1] in (0xC3,0xC2,0xCC,0x90,0xE9,0xEB): pro.append((v+k, '55 8B EC'))
  if b[k:k+3]==b'\x8b\xff\x55': pro.append((v+k+1,'8B FF 55'))
# direct branch/call target census
tgt=collections.Counter()
# (simple exact rel32 targets from e8/e9 and rel8 7x/eb) - overinclusive but useful
for i,(v,vs,rp,rs,ch) in enumerate(SEC):
 if not ch&0x20000000:continue
 b=D[rp:rp+rs]
 for k in range(len(b)-5):
  op=b[k]
  if op in (0xE8,0xE9):
   t=v+k+5+struct.unpack_from('<i',b,k+1)[0]
   if sec(t):tgt[t]+=1
  elif 0x70<=op<=0x7F or op==0xEB:
   t=v+k+2+struct.unpack_from('<b',b,k+1)[0]
   if sec(t):tgt[t]+=1
print('prologues',len(pro),'unique',len(set(x[0] for x in pro)))
# nearest prologue to callsite
pl=sorted(set(x[0] for x in pro))
for a in [0x237C15,0x237C0D,0x237C00,0x237C25]:
 i=bisect.bisect_right(pl,a)-1
 print('addr',hex(a),'nearest_prologue',hex(pl[i]) if i>=0 else None,'delta',a-pl[i] if i>=0 else None,'direct_target_count',tgt.get(a,0))
# direct targets in vicinity
print('nearby targets',[(hex(x),tgt[x]) for x in sorted(tgt) if 0x237B00<=x<=0x237E00])
# validate candidate prologue and disasm
md=None
from capstone import *
from capstone.x86 import *
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
for a in [pl[bisect.bisect_right(pl,0x237C15)-1]]:
 print('\ncandidate',hex(a),'file',hex(r2o(a)))
 for ins in md.disasm(D[r2o(a):r2o(a)+160],IB+a):
  print('%08X %-18s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=IB+a+120:break
