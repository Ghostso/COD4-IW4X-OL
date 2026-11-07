import struct, collections
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
D=Path('codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; osz=struct.unpack_from('<H',D,pe+20)[0]; so=opt+osz
SEC=[]
for i in range(n):
 h=so+40*i; name=D[h:h+8].split(b'\0')[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); ch=struct.unpack_from('<I',D,h+36)[0]; SEC.append(dict(i=i,name=name,va=va,vs=vs,rs=rs,pr=pr,ch=ch))
def sec(rva):
 for s in SEC:
  if s['va']<=rva<s['va']+max(s['vs'],s['rs']): return s
 return None
def off(rva):
 s=sec(rva)
 if not s:return None
 q=rva-s['va']; return s['pr']+q if 0<=q<s['rs'] else None
def u32(r):
 f=off(r); return struct.unpack_from('<I',D,f)[0] if f is not None and f+4<=len(D) else None
def is_exec(r):
 s=sec(r); return bool(s and s['name']!='.tvm0' and s['ch']&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def dis(start,limit=0x10000):
 f=off(start); s=sec(start)
 if f is None or not is_exec(start):return []
 lim=min(limit,len(D)-f,s['vs']-(start-s['va']))
 return list(md.disasm(D[f:f+lim],IB+start))
def exports():
 er,sz=struct.unpack_from('<II',D,opt+96)
 if not er or off(er) is None:return []
 nf=u32(er+24); af=u32(er+28); nn=u32(er+32); an=u32(er+36); out=[]
 for i in range(nf):
  r=u32(af+4*i); nm=''
  if i<nn:
   o=off(an+4*i)
   if o: nm=D[o:].split(b'\0',1)[0].decode('latin1')
  out.append((r,nm))
 return out
exps=exports(); roots=[r for r,n in exps if r is not None and is_exec(r)]+[0x0e5dc690]
# BFS direct/fallthrough CFG. Root changes on direct calls. Record first predecessor per exact instruction.
pred={}; dist={}; owner=collections.defaultdict(set); q=collections.deque()
for r in roots:
 if is_exec(r): pred[r]=None; dist[r]=0; q.append(r)
while q:
 start=q.popleft()
 for x in dis(start):
  a=x.address-IB
  if a!=start and a in dist: continue
  if a!=start:
   dist[a]=dist[start]+1; pred[a]=start
  owner[a].add(start)
  m=x.mnemonic; ops=x.operands
  if m in ('ret','retn','iret','iretd','ud2','int3'): break
  if m=='call':
   nxt=(a+x.size)
   if is_exec(nxt) and nxt not in dist:
    pred[nxt]=a; dist[nxt]=dist[start]+1; q.append(nxt)
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB
    if is_exec(t) and t not in dist:
     pred[t]=a; dist[t]=dist[start]+1; q.append(t)
   continue
  if m.startswith('j'):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB
    if is_exec(t) and t not in dist:
     pred[t]=a; dist[t]=dist[start]+1; q.append(t)
   if m=='jmp': break
  else:
   nxt=a+x.size
   if is_exec(nxt) and nxt not in dist:
    pred[nxt]=a; dist[nxt]=dist[start]+1; q.append(nxt)
for target in (0x3667a,0x36691):
 print('\nTARGET',hex(target),'in_cfg',target in dist,'dist',dist.get(target))
 chain=[]; p=target
 while p is not None:
  chain.append(p); p=pred.get(p)
 chain.reverse()
 print('PATH',' -> '.join(hex(a) for a in chain))
 for a in chain:
  z=next(md.disasm(D[off(a):off(a)+16],IB+a,count=1),None)
  print(hex(a),z.mnemonic+' '+z.op_str if z else '?')
