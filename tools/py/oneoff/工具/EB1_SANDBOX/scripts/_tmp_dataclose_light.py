from pathlib import Path
import struct, collections, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG
EXE=Path('codoMP_client_shipRetail.exe'); OUT=Path('scripts/_out'); D=EXE.read_bytes(); IB=0x400000
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
 q=r-s['va'];return s['pr']+q if 0<=q<s['rs'] else None
def rd(r,n):o=off(r);return D[o:o+n] if o is not None and o+n<=len(D) else None
def u32(r):b=rd(r,4);return struct.unpack('<I',b)[0] if b else None
def ex(r):
 s=sec(r);return bool(s and s['name'].lower()!='.tvm0' and s['ch']&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
def dec(r,n=0x400,count=0):
 o=off(r);s=sec(r)
 if o is None or not s or s['name'].lower()=='.tvm0':return []
 lim=min(n,len(D)-o,s['rs']-(r-s['va']));return list(md.disasm(D[o:o+lim],IB+r,count=count)) if lim>0 else []
def txt(i):return (i.mnemonic+' '+i.op_str).strip()
# clean roots entry+exports
er,_=struct.unpack_from('<II',D,opt+96);roots=[struct.unpack_from('<I',D,opt+16)[0]]
if er and off(er) is not None:
 nf=u32(er+24);af=u32(er+28)
 for i in range(nf or 0):
  x=u32(af+4*i)
  if x is not None and ex(x):roots.append(x)
q=collections.deque((r,r) for r in sorted(set(roots)));seen=set();owner=collections.defaultdict(set);insmap={}
while q:
 root,start=q.popleft();key=(root,start)
 if key in seen or not ex(start):continue
 seen.add(key)
 for i in dec(start,0x10000):
  a=i.address-IB;owner[a].add(root);insmap[a]=i
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
print('CLEAN roots',len(set(roots)),'insns',len(insmap))
# selected mov/call exact matches
selected=[0x746a,0x97fc,0xc51b,0x1f5e4,0x2acf0,0x5038f,0xa7f0a,0xb9f25,0xbfc4a,0x15260f,0x1fcc88,0x213d6d,0x2255be,0x23db1e,0x2a18db,0x6b47d,0x222edb,0x27dced,0x284f34]
# exact relative incoming edges, scanning opcodes and validating source
inc=collections.defaultdict(list)
for s in S:
 if s['name'].lower()=='.tvm0' or not(s['ch']&0x20000000):continue
 b=D[s['pr']:s['pr']+s['rs']]
 for j in range(len(b)):
  src=s['va']+j; tgt=None; kind=None; sz=0
  if j+5<=len(b) and b[j] in (0xe8,0xe9):
   tgt=src+5+struct.unpack_from('<i',b,j+1)[0];kind='CALL' if b[j]==0xe8 else 'JMP';sz=5
  elif j+6<=len(b) and b[j]==0x0f and 0x80<=b[j+1]<=0x8f:
   tgt=src+6+struct.unpack_from('<i',b,j+2)[0];kind='JCC';sz=6
  elif j+2<=len(b) and (0x70<=b[j]<=0x7f or b[j]==0xeb):
   tgt=src+2+struct.unpack_from('<b',b,j+1)[0];kind='JCC_SHORT' if b[j]!=0xeb else 'JMP_SHORT';sz=2
  if tgt in selected:
   z=dec(src,16,1)
   if z and z[0].address-IB==src and z[0].size==sz:inc[tgt].append(dict(src=src,kind=kind,text=txt(z[0])))
print('INCOMING')
for r in selected:print(hex(r),'cfg',sorted(owner.get(r,[]))[:6],'in',inc.get(r,[]))
print('\nWINDOWS')
for r in selected:
 z=dec(r,16,1);cur=r+(z[0].size if z else 0);print('POINT',hex(r),txt(z[0]) if z else '' ,'cfg',sorted(owner.get(r,[])))
 for i in dec(r-40,100):print('  %08X %-24s %s'%(i.address-IB,i.bytes.hex(),txt(i)))
 print('  POST')
 for i in dec(cur,64,10):print('   %08X %-16s %s'%(i.address-IB,i.bytes.hex(),txt(i)))
# CA8114/CA8194 five pair exact matrices
pairs=[(0x269ae,0x269c6),(0x3667a,0x36691),(0xaa17b,0xaa192),(0xb2d95,0xb2dac),(0x21da25,0x21da3c)]
print('\nPAIR MATRIX')
for a,b in pairs:
 za=dec(a,16,1)[0];zb=dec(b,16,1)[0]
 print(hex(a),hex(b),'delta',b-a,'self',txt(za),'/',txt(zb),'cfg',sorted(owner.get(a,[])),sorted(owner.get(b,[])),'eq32',rd(a,32)==rd(b,32),'eq48',rd(a,48)==rd(b,48),'eq64',rd(a,64)==rd(b,64))
# CA812C post global writes and CA819C pre push values
print('\nCA812C POST WRITES')
for r in [0x29c57,0x30d3b,0x351ea,0x39f52,0x4970c,0x50b04,0x55f10,0x5a0d3,0x6dc64,0xab745,0xaeb28,0xc0574,0xd0ce8,0x1162e2,0x11cfcb,0x123c12,0x12a97f,0x14fe00,0x158b2a,0x15d05d,0x1604a5,0x168138,0x1861a2,0x19a2a5,0x1d21df,0x1d838c,0x1e5db0,0x1e89b7,0x1fb951,0x21b0c0,0x221499,0x22540a,0x233495,0x266e12,0x2693cd,0x26ac19,0x280a6e,0x28d714,0x4eeb3e]:
 z=dec(r,16,1);cur=r+(z[0].size if z else 0);w=[]
 for i in dec(cur,48,8):
  for o in i.operands:
   if o.type==CS_OP_MEM and o.mem.base==0 and o.mem.index==0 and o.mem.disp in (0x81aa110,0x81aa114):w.append((i.address-IB,txt(i),hex(o.mem.disp)))
 print(hex(r),w)
print('\nCA819C PRE PUSH')
for r in [0x35868,0x694d1,0x6fbea,0x7e653,0x84aca,0x86f43,0x90600,0x9847f,0xa7a6c,0xbfeb0,0xccd8f,0x12230a,0x129457,0x13cfdc,0x1401e2,0x147b69,0x14c448,0x15a166,0x15ba5b,0x161c16,0x168805,0x175831,0x1849ef,0x1db4de,0x215689,0x23419a,0x2516e6,0x2628c1,0x29e7c3,0x2a3dfb,0x2a6312,0x2c82c9,0x45d3b8,0x4ce922,0x55bcf7,0x56521b]:
 pre=[]
 for k in range(1,16):
  z=dec(r-k,16,1)
  if z and z[0].address-IB==r-k and z[0].address-IB+z[0].size==r:pre.append((r-k,z[0].bytes.hex(),txt(z[0])))
 print(hex(r),pre[:3])
# CA8164 exact comparison post
print('\nCA8164 POST CMP')
for r in [x for x in [0x2f35,0x2695b,0x397da,0x49e45,0x517fa,0x58a67,0x5ba86,0x6b358,0x9a3b6,0x121f08,0x12372b,0x130662,0x133c79,0x138005,0x14a46c,0x14c72f,0x1606ba,0x163f16,0x18f388,0x1ae465,0x1bcebd,0x21db37,0x229207,0x231ff8,0x239fbe,0x2669ad,0x286c6c,0x292287,0x29c636,0x2c41e0,0x5557e8,0x55a12a]]:
 z=dec(r,16,1);cur=r+(z[0].size if z else 0);term=[]
 for i in dec(cur,24,3):term.append((i.address-IB,txt(i)))
 print(hex(r),term)
