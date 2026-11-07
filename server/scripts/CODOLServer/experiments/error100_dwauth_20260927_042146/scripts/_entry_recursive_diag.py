# read-only diagnostic: recursive candidate boundaries, no .tvm0 payload read
import struct,pathlib,collections
from capstone import *
from capstone.x86 import *
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; SOI=0xE659000
SECS=[(0,'.tp3',0x1000,0x8A689A,0x1000,0x593000,0x60000020),(1,'.tp3',0x8A8000,0x16DA70,0x594000,0x16E000,0x40000040),(2,'.tp3',0xA16000,0xDBB1CC0,0x702000,0x62000,0xC0000040),(3,'.tp3',0xE5C8000,0x31,0x764000,0x1000,0xC0000040),(4,'.tp3',0xE5C9000,0x9228,0x765000,0xA000,0x40000040),(5,'.tvm0',0xE5D3000,0x4000,0x76F000,0x2000,0x60000020),(6,'.tp3',0xE5D7000,0x82000,0x771000,0x6000,0xE0000020)]
for s in SECS:
 if s[1]=='.tvm0': continue
 # read only permitted section's raw payload
 # (bytes already in D but no offsets from .tvm0 used below)
 pass
def sec(rva):
 for s in SECS:
  if s[1]=='.tvm0': continue
  if s[2]<=rva<s[2]+max(s[3],s[5]): return s
 return None
def r2o(rva):
 s=sec(rva)
 if not s:return None
 x=rva-s[2]
 return s[4]+x if 0<=x<s[5] else None
def exec_at(rva):
 s=sec(rva); return bool(s and s[6]&0x20000000)
def read32(rva):
 o=r2o(rva); return struct.unpack_from('<I',D,o)[0] if o is not None and o+4<=len(D) else None
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def one(rva):
 o=r2o(rva)
 if o is None:return None
 return next(md.disasm(D[o:o+15],IB+rva,count=1),None)
def traverse(fn,insmap,seen,todo):
 if fn in seen or not exec_at(fn):return
 seen.add(fn); rva=fn; n=0
 while n<300000:
  n+=1
  if not exec_at(rva) or rva in insmap:return
  ins=one(rva)
  if ins is None:return
  insmap[rva]=ins
  if ins.mnemonic=='call' and ins.operands and ins.operands[0].type==X86_OP_IMM:
   t=int(ins.operands[0].imm)-IB
   if exec_at(t):todo.append(t)
  elif ins.mnemonic=='jmp':
   if ins.operands and ins.operands[0].type==X86_OP_IMM:
    t=int(ins.operands[0].imm)-IB
    if exec_at(t):todo.append(t)
   return
  elif ins.mnemonic.startswith('j') and ins.operands and ins.operands[0].type==X86_OP_IMM:
   t=int(ins.operands[0].imm)-IB
   if exec_at(t):todo.append(t)
  elif ins.mnemonic in ('ret','retf','iret','hlt','ud2','int3'):
   return
  rva+=ins.size
insmap={};seen=set();todo=collections.deque([0xE5DC690]);seedn=0;seeds=set()
while todo:traverse(todo.popleft(),insmap,seen,todo)
for s in SECS:
 if s[1]=='.tvm0' or not s[6]&0x20000000:continue
 b=D[s[4]:s[4]+s[5]]
 for k in range(len(b)-4):
  if b[k]==0xE8:
   t=s[2]+k+5+struct.unpack_from('<i',b,k+1)[0]
   if exec_at(t) and t not in seen:
    seedn+=1;seeds.add(t);todo.append(t)
while todo:traverse(todo.popleft(),insmap,seen,todo)
print('map',len(insmap),'functions',len(seen),'seed_candidates',seedn)
events=[]
for rva,ins in insmap.items():
 if len(ins.bytes)>=2 and ins.bytes[0]==0xff and ins.bytes[1] in (0x15,0x25):
  op=ins.operands[0] if ins.operands else None
  if op and op.type==X86_OP_MEM and op.mem.base==0 and op.mem.index==0:
   va=int(op.mem.disp)&0xffffffff
   if IB<=va<IB+SOI:
    val=read32(va-IB); nxt=read32(va-IB+4)
   else:val=nxt=None
   events.append((rva,ins.bytes[1],va,val,nxt))
print('events',len(events),'ff15',sum(x[1]==0x15 for x in events),'ff25',sum(x[1]==0x25 for x in events))
print('direct8',sum(0x80000000<=x[2]<=0x8fffffff for x in events))
sent=[x for x in events if x[3] is not None and 0x80000000<=x[3]<=0x8fffffff]
exactpair=[x for x in sent if x[3]==0x80000001 and x[4]==0]
print('slot_sentinel',len(sent),'distinct',len({x[2] for x in sent}),'exact_pair',len(exactpair))
for x in sorted(exactpair): print('EXACTPAIR',hex(x[0]),'FF%02X'%x[1],hex(x[2]),hex(x[3]),hex(x[4]))
print('top sentinel slots')
for slot,c in collections.Counter(x[2] for x in sent).most_common(30):
 val=read32(slot-IB);print(hex(slot),c,hex(val))
print('entryrefs',[(hex(rva),hex(va),hold,hex(val) if val is not None else None,hex(nxt) if nxt is not None else None) for rva,hold,va,val,nxt in events if va==0xE9DC665])
