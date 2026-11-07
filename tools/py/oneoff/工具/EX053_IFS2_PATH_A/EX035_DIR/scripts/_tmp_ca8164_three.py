from pathlib import Path
import json, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG
EXE=Path('codoMP_client_shipRetail.exe'); D=EXE.read_bytes(); IB=0x400000
pe=struct.unpack_from('<I',D,0x3c)[0]; n=struct.unpack_from('<H',D,pe+6)[0]; opt=pe+24; ots=struct.unpack_from('<H',D,pe+20)[0]; so=opt+ots
S=[]
for i in range(n):
 h=so+40*i; name=D[h:h+8].split(b'\0',1)[0].decode('latin1'); vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8); ch=struct.unpack_from('<I',D,h+36)[0]; S.append(dict(i=i,name=name,vs=vs,va=va,rs=rs,pr=pr,ch=ch))
def sec(r):
 for s in S:
  if s['va']<=r<s['va']+max(s['vs'],s['rs']): return s
def off(r):
 s=sec(r)
 if not s or s['name']=='.tvm0': return None
 q=r-s['va']; return s['pr']+q if 0<=q<s['rs'] else None
def rd(r,n): o=off(r); return D[o:o+n] if o is not None and o+n<=len(D) else None
def dis(r,n=80):
 o=off(r); 
 if o is None:return []
 return list(md.disasm(D[o:o+n],IB+r))
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# exact user points and all CA8164 mov/call byte pairs
for pair in [(0x746a,0x7471),(0x97fc,0x9804),(0xc51b,0xc524),(0x1f5e4,0x1f5ec),(0x2acf0,0x2acf7),(0x5038f,0x50397),(0xa7f0a,0xa7f11),(0xb9f25,0xb9f2b),(0xbfc4a,0xbfc50),(0x15260f,0x152615),(0x1fcc88,0x1fcc8e),(0x213d6d,0x213d73),(0x2255be,0x2255c4),(0x23db1e,0x23db25),(0x2a18db,0x2a18e1),(0x6b47d,None),(0x222edb,None)]:
 print('\nPAIR',hex(pair[0]),hex(pair[1]) if pair[1] else 'NONE')
 print(' bytes',rd(pair[0],32).hex() if rd(pair[0],32) else None)
 for x in dis(pair[0]-32,96): print('  %08X %-24s %s'%(x.address-IB,x.bytes.hex(),x.mnemonic+' '+x.op_str))
# validation of all 0x8B /0 disp32 references to CA8164
print('\nALL MOV LOAD BYTE HITS')
for s in S:
 if s['name']=='.tvm0':continue
 b=D[s['pr']:s['pr']+s['rs']]
 for p in range(8):
  pat=b'\x8b'+bytes([p*8+5])+struct.pack('<I',0x00ca8164)
  q=0
  while True:
   q=b.find(pat,q)
   if q<0:break
   r=s['va']+q; z=dis(r,16)
   ok=bool(z and z[0].address-IB==r and z[0].mnemonic=='mov')
   print('%08X ok=%s %s'%(r,ok,z[0].mnemonic+' '+z[0].op_str if z else ''))
   q+=1
