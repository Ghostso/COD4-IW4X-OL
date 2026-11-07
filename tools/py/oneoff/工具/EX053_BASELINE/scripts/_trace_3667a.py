import struct
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from capstone.x86 import X86_OP_IMM
P=Path("codoMP_client_shipRetail.exe"); IB=0x400000
with P.open("rb") as f:
 h=f.read(0x1000); pe=struct.unpack_from("<I",h,0x3c)[0]; n=struct.unpack_from("<H",h,pe+6)[0]; osz=struct.unpack_from("<H",h,pe+20)[0]; opt=h[pe+24:pe+24+osz]; so=pe+24+osz; sh=f.read(40*n); secs=[]
 for i in range(n):
  b=sh[40*i:40*(i+1)]; name=b[:8].split(b"\0",1)[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",b,8); ch=struct.unpack_from("<I",b,36)[0]; secs.append((name,va,vs,rs,pr,ch))
 data={}
 for i,(name,va,vs,rs,pr,ch) in enumerate(secs):
  if name.lower()==".tvm0":continue
  f.seek(pr); data[i]=f.read(rs)
def sec(r):
 for i,(name,va,vs,rs,pr,ch) in enumerate(secs):
  if va<=r<va+max(vs,rs):return i,name,va,vs,rs,pr,ch
 return None
def rd(r,n):
 z=sec(r)
 if not z:return None
 i,name,va,vs,rs,pr,ch=z; q=r-va
 return data[i][q:q+n] if 0<=q and q+n<=rs else None
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# exact linear decode from every candidate export start to 0x36700, noting alignment
for st in (0x362d0,0x363f0,0x36460,0x36470,0x36480,0x36490,0x364a0,0x364f0):
 b=rd(st,0x500)
 print("\\nSTART",hex(st),"first",b[:16].hex() if b else None)
 if not b:continue
 hit=False
 for x in md.disasm(b,IB+st):
  a=x.address-IB
  if a in (0x3667a,0x36691):hit=True;print(" HIT",hex(a),x.bytes.hex(),x.mnemonic,x.op_str)
  if a>0x366a0:break
 print(" linear_hit",hit)
# Recursive trace with predecessor capture from 364f0.
start=0x364f0; target=0x3667a
q=[start]; seen=set(); pred={}; decoded={}
while q:
 st=q.pop(0)
 if st in seen:continue
 seen.add(st); b=rd(st,0x4000)
 if not b:continue
 for x in md.disasm(b,IB+st):
  a=x.address-IB; decoded[a]=x
  if a>=target:break
  m=x.mnemonic; ops=x.operands
  if m in ("ret","retn","iret","iretd","ud2","int3"):break
  if m=="call":
   if ops and ops[0].type==X86_OP_IMM:
    t=ops[0].imm-IB; pred.setdefault(t,(a,st));q.append(t)
   continue
  if m.startswith("j"):
   if ops and ops[0].type==X86_OP_IMM:
    t=ops[0].imm-IB; pred.setdefault(t,(a,st));q.append(t)
   if m=="jmp":break
   continue
  n=a+x.size;pred.setdefault(n,(a,st))
print("recursive",target in decoded, "seen",len(seen))
if target in pred:print("pred",hex(pred[target][0]),"chunk_start",hex(pred[target][1]))
for a in sorted(x for x in decoded if 0x36650<=x<=0x366a0):print(hex(a),decoded[a].bytes.hex(),decoded[a].mnemonic,decoded[a].op_str)
