# read-only corrected follow-up; recursive candidate boundaries, no .tvm0 payload offsets used
import struct,pathlib,collections
from capstone import *
from capstone.x86 import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; SOI=0xE659000
SECS=[(0,'.tp3',0x1000,0x593000,0x1000,0x60000020),(1,'.tp3',0x8A8000,0x16E000,0x594000,0x40000040),(2,'.tp3',0xA16000,0x62000,0x702000,0xC0000040),(3,'.tp3',0xE5C8000,0x1000,0x764000,0xC0000040),(4,'.tp3',0xE5C9000,0xA000,0x765000,0x40000040),(6,'.tp3',0xE5D7000,0x6000,0x771000,0xE0000020)]
def sec(rva):
 for s in SECS:
  if s[2]<=rva<s[2]+s[3]:return s
 return None
def r2o(rva):
 s=sec(rva)
 return None if s is None else s[4]+rva-s[2]
def ex(rva):
 s=sec(rva);return bool(s and s[5]&0x20000000)
def rd32(rva):
 o=r2o(rva);return None if o is None or o+4>len(D) else struct.unpack_from('<I',D,o)[0]
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def one(rva):
 o=r2o(rva);return None if o is None else next(md.disasm(D[o:o+15],IB+rva,count=1),None)
def trav(fn,M,seen,Q):
 if fn in seen or not ex(fn):return
 seen.add(fn);rva=fn
 while 1:
  if not ex(rva) or rva in M:return
  i=one(rva)
  if not i:return
  M[rva]=i
  if i.mnemonic=='call' and i.operands and i.operands[0].type==X86_OP_IMM:
   t=int(i.operands[0].imm)-IB
   if ex(t):Q.append(t)
  elif i.mnemonic=='jmp':
   if i.operands and i.operands[0].type==X86_OP_IMM:
    t=int(i.operands[0].imm)-IB
    if ex(t):Q.append(t)
   return
  elif i.mnemonic.startswith('j') and i.operands and i.operands[0].type==X86_OP_IMM:
   t=int(i.operands[0].imm)-IB
   if ex(t):Q.append(t)
  elif i.mnemonic in ('ret','retf','iret','hlt','ud2','int3'):return
  rva+=i.size
M={};seen=set();Q=collections.deque([0xE5DC690]);seedn=0;seeds=set()
while Q:trav(Q.popleft(),M,seen,Q)
for s in SECS:
 b=D[s[4]:s[4]+s[3]]
 if not s[5]&0x20000000:continue
 for k in range(len(b)-4):
  if b[k]==0xE8:
   t=s[2]+k+5+struct.unpack_from('<i',b,k+1)[0]
   if ex(t) and t not in seen:
    seedn+=1;seeds.add(t);Q.append(t)
while Q:trav(Q.popleft(),M,seen,Q)
E=[]
for rva,i in M.items():
 if len(i.bytes)>=2 and i.bytes[0]==0xff and i.bytes[1] in (0x15,0x25):
  o=i.operands[0] if i.operands else None
  if o and o.type==X86_OP_MEM and o.mem.base==0 and o.mem.index==0:
   va=int(o.mem.disp)&0xffffffff;val=rd32(va-IB) if IB<=va<IB+SOI else None
   E.append((rva,i,va,val))
print('MAP',len(M),'FUNCTIONS',len(seen),'SEEDS',seedn,'EVENTS',len(E))
print('DIRECT8')
for rva,i,va,val in sorted(E):
 if 0x80000000<=va<=0x8fffffff:
  print(hex(rva),i.bytes.hex(),i.mnemonic,i.op_str,'direct',hex(va),'slotvalue',hex(val) if val is not None else '-','next',hex(rd32(va-IB+4)) if val is not None else '-')
print('SLOT8')
for rva,i,va,val in sorted(E):
 if val is not None and 0x80000000<=val<=0x8fffffff:
  print(hex(rva),i.bytes.hex(),i.mnemonic,i.op_str,'operand',hex(va),'value',hex(val),'next',hex(rd32(va-IB+4)))
print('NEAR8')
for rva,i,va,val in sorted(E):
 if val is None:continue
 hits=[]
 for d in range(-16,17,4):
  nv=rd32(va-IB+d)
  if nv is not None and 0x80000000<=nv<=0x8fffffff:hits.append((d,nv))
 if hits:print(hex(rva),hex(va),'exact',hex(val),'hits',[(d,hex(v)) for d,v in hits])
print('DIRECT_E8_TO_ENTRY')
for s in SECS:
 b=D[s[4]:s[4]+s[3]]
 for k in range(len(b)-4):
  if b[k] in (0xE8,0xE9):
   t=s[2]+k+5+struct.unpack_from('<i',b,k+1)[0]
   if t==0xE5DC690:print('raw',hex(s[2]+k),'op',hex(b[k]),'target',hex(t),'candidate_boundary',s[2]+k in M)
print('CANDIDATE_DIRECT_TARGET_ENTRY',[(hex(rva),hex(i.bytes[0]),i.op_str) for rva,i in M.items() if i.mnemonic in ('call','jmp') and i.operands and i.operands[0].type==X86_OP_IMM and int(i.operands[0].imm)==0xE9DC690])
