import pathlib,struct,collections,heapq
from capstone import *
from capstone.x86 import X86_OP_IMM
D=pathlib.Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
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
def ex(r):
 s=sec(r); return bool(s and s[-1]&0x20000000)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def one(r):
 o=r2o(r); return next(md.disasm(D[o:o+15],IB+r,count=1),None) if o is not None else None
# Build over-seeded instruction map, preserving predecessor edges.
insmap={}; preds=collections.defaultdict(set); todo=collections.deque([0xE5DC690]); seen_fn=set()
# add all direct E8 targets as roots
for i,(v,vs,rp,rs,ch) in enumerate(SEC):
 if not ch&0x20000000: continue
 b=D[rp:rp+rs]
 for k in range(len(b)-4):
  if b[k]==0xE8:
   t=v+k+5+struct.unpack_from('<i',b,k+1)[0]
   if ex(t): todo.append(t)
# also add a few obvious prologue candidates? leave for later
def walk(fn):
 if fn in seen_fn or not ex(fn): return
 seen_fn.add(fn); r=fn
 for _ in range(200000):
  if not ex(r) or r in insmap: return
  ins=one(r)
  if not ins: return
  insmap[r]=ins
  nxt=r+ins.size
  ops=ins.operands; mn=ins.mnemonic
  def add(t):
   if ex(t): preds[t].add(r); todo.append(t)
  if mn=='call':
   if ops and ops[0].type==X86_OP_IMM: add(int(ops[0].imm)-IB)
   # fallthrough
  elif mn=='jmp':
   if ops and ops[0].type==X86_OP_IMM: add(int(ops[0].imm)-IB)
   return
  elif mn.startswith('j') and ops and ops[0].type==X86_OP_IMM: add(int(ops[0].imm)-IB)
  elif mn in ('ret','retf','iret','hlt','ud2','int3'): return
  r=nxt
while todo: walk(todo.popleft())
print('fn_roots',len(seen_fn),'ins',len(insmap),'preds',len(preds))
# identify candidate starts for 0x237C15 and nearby block entry 0x237C00-ish
for a in (0x237C00,0x237C0D,0x237C15,0x237C1B,0x237C25):
 print('addr',hex(a),'inmap',a in insmap,'preds',[hex(x) for x in sorted(preds.get(a,[]))])
# predecessors of instruction containing 237c15: scan insmap for spans covering it
covering=[]
for a,ins in insmap.items():
 if a<=0x237C15<a+ins.size: covering.append((a,ins))
print('covering',[(hex(a),ins.size,ins.mnemonic) for a,ins in covering])
# Try find direct jump/call target exactly 237c15 and nearest roots <= address
roots=sorted(seen_fn)
print('nearest roots <=', [hex(x) for x in roots if x<=0x237C15][-20:])
print('roots >', [hex(x) for x in roots if x>0x237C15][:20])
# dump instructions around validated predecessor blocks if present
for va in (0x237B80,0x237BC0,0x237BE0,0x237BF0,0x237C00,0x237C0A,0x237C15,0x237C1B):
 print('\n',hex(va))
 for ins in md.disasm(D[r2o(va):r2o(va)+48],IB+va):
  print('%08X %-16s %s'%(ins.address,ins.bytes.hex(),ins.mnemonic+' '+ins.op_str))
  if ins.address>=IB+va+32:break
