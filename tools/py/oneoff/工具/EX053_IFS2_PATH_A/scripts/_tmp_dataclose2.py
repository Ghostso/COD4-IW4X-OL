from pathlib import Path
import struct, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
EXE=Path('codoMP_client_shipRetail.exe'); D=EXE.read_bytes(); IB=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; ots=struct.unpack_from('<H',D,pe+20)[0]; so=opt+ots
S=[]
for i in range(n):
 h=so+40*i; name=D[h:h+8].split(b'\0',1)[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); ch=struct.unpack_from('<I',D,h+36)[0]; S.append(dict(i=i,name=name,vs=vs,va=va,rs=rs,pr=pr,ch=ch))
def sec(r):
 for s in S:
  if s['va']<=r<s['va']+max(s['vs'],s['rs']):return s
def off(r):
 s=sec(r)
 if not s or s['name'].lower()=='.tvm0':return None
 q=r-s['va']; return s['pr']+q if 0<=q<s['rs'] else None
def rd(r,n):
 o=off(r); return D[o:o+n] if o is not None and o+n<=len(D) else None
def u32(r):
 b=rd(r,4); return struct.unpack('<I',b)[0] if b else None
def ex(r):
 s=sec(r); return bool(s and s['name'].lower()!='.tvm0' and s['ch']&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def dec(r,n=0x800,count=0):
 o=off(r);s=sec(r)
 if o is None or not s or s['name'].lower()=='.tvm0':return []
 lim=min(n,len(D)-o,s['rs']-(r-s['va']));return list(md.disasm(D[o:o+lim],IB+r,count=count)) if lim>0 else []
def txt(i):return (i.mnemonic+' '+i.op_str).strip()
er,esz=struct.unpack_from('<II',D,opt+96); roots=[]
if er and off(er) is not None:
 nf=u32(er+24);af=u32(er+28)
 for i in range(nf or 0):
  x=u32(af+4*i)
  if x is not None and ex(x):roots.append(x)
roots.append(struct.unpack_from('<I',D,opt+16)[0])
for s in S:
 if s['name'].lower()=='.tvm0' or not(s['ch']&0x20000000):continue
 b=D[s['pr']:s['pr']+s['rs']]
 for j in range(len(b)-5):
  if b[j]==0xe8:
   t=s['va']+j+5+struct.unpack_from('<i',b,j+1)[0]
   if ex(t):roots.append(t)
q=collections.deque((r,r) for r in sorted(set(roots)));seen=set();ins_roots=collections.defaultdict(set)
while q:
 root,start=q.popleft();key=(root,start)
 if key in seen or not ex(start):continue
 seen.add(key)
 for i in dec(start,0x10000):
  a=i.address-IB;ins_roots[a].add(root)
  if i.mnemonic in ('ret','retn','iret','iretd','ud2','int3'):break
  if i.mnemonic=='call':
   if i.operands and i.operands[0].type==CS_OP_IMM:
    t=i.operands[0].imm-IB
    if ex(t):q.append((t,t))
   continue
  if i.mnemonic.startswith('j'):
   if i.operands and i.operands[0].type==CS_OP_IMM:
    t=i.operands[0].imm-IB
    if ex(t):q.append((root,t))
   if i.mnemonic=='jmp':break
  nx=a+i.size
  if ex(nx):q.append((root,nx))
selected=[0x746a,0x97fc,0xc51b,0x1f5e4,0x2acf0,0x5038f,0xa7f0a,0xb9f25,0xbfc4a,0x15260f,0x1fcc88,0x213d6d,0x2255be,0x23db1e,0x2a18db,0x6b47d,0x222edb]
incoming=collections.defaultdict(list)
for a,rs in ins_roots.items():
 z=dec(a,16,1)
 if not z:continue
 i=z[0];t=None
 if i.mnemonic in ('call','jmp','jcc') or i.mnemonic.startswith('j'):
  if i.operands and i.operands[0].type==CS_OP_IMM:t=i.operands[0].imm-IB
 if t in selected:incoming[t].append((a,txt(i),sorted(rs)))
 nx=a+i.size
 if nx in selected and i.mnemonic not in ('jmp','ret','retn','iret','iretd','ud2','int3'):incoming[nx].append((a,txt(i),sorted(rs)))
print('ROOT COUNT',len(set(roots)))
for r in selected:
 z=dec(r,16,1);print('POINT',hex(r),txt(z[0]) if z else 'no self decode','cfg_roots',sorted(ins_roots.get(r,[]))[:10],'incoming',incoming.get(r,[])[:16])
print('\nPOST')
for r in selected:
 z=dec(r,16,1);cur=r+(z[0].size if z else 0);print('POST',hex(r))
 for i in dec(cur,96,8):print('  %08X %s'%(i.address-IB,txt(i)))
print('\nPAIR BLOCK COMPARISON')
for a,b in [(0x269ae,0x269c6),(0x3667a,0x36691),(0xaa17b,0xaa192),(0xb2d95,0xb2dac),(0x21da25,0x21da3c)]:
 print(hex(a),hex(b),[(L,rd(a,L)==rd(b,L)) for L in (32,48,64)])
print('\nCA819C IMMEDIATE CONTEXT')
for s in S:
 if s['name'].lower()=='.tvm0':continue
 b=D[s['pr']:s['pr']+s['rs']]
 for r in range(len(b)-6):
  if b[r:r+6]!=b'\xff\x15\x9c\x81\xca\x00':continue
  rr=s['va']+r;pred=[]
  for k in range(1,16):
   z=dec(rr-k,32)
   if z and z[0].address-IB==rr-k and z[0].address-IB+z[0].size==rr:pred.append((rr-k,z[0].bytes.hex(),txt(z[0])))
  print(hex(rr),'pred',pred[:5])
print('\nTABLE')
print('entry_80000001',[(hex(0xca8000+4*i),hex(u32(0x8a8000+4*i))) for i in range(512) if u32(0x8a8000+4*i)==0x80000001])
print('sentinel_count',sum(1 for i in range(512) if u32(0x8a8000+4*i) is not None and 0x80000000<=u32(0x8a8000+4*i)<=0x8fffffff))
