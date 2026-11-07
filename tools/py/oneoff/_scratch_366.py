import struct
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32,CS_OP_IMM
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; n=struct.unpack_from("<H",D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from("<H",D,pe+20)[0]; secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); ch=struct.unpack_from("<I",D,h+36)[0]; secs.append((i,nm,va,vs,rs,pr,ch))
def sec(r):
 for s in secs:
  i,nm,va,vs,rs,pr,ch=s
  if va<=r<va+rs:return s
 return None
def off(r):
 s=sec(r)
 if not s:return None
 return s[5]+r-s[2]
def u32(r):
 o=off(r); return struct.unpack_from("<I",D,o)[0] if o is not None and o+4<=len(D) else None
def cstr(r):
 o=off(r); return D[o:o+256].split(b"\0",1)[0].decode("latin1") if o is not None else ""
def is_exec(r):
 s=sec(r); return bool(s and s[1] != ".tvm0" and s[6]&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
def dis(start,maxlen=0x10000):
 o=off(start); s=sec(start)
 if o is None or not is_exec(start):return []
 lim=min(maxlen,len(D)-o,s[3]-(start-s[2]))
 return list(md.disasm(D[o:o+lim],0x400000+start))
# EAT roots
er,es=struct.unpack_from("<II",D,opt+96); nf=u32(er+24); af=u32(er+28); roots=[]
for i in range(nf):
 r=u32(af+4*i)
 if r and is_exec(r): roots.append(r)
entry=struct.unpack_from("<I",D,opt+40)[0]
print("entry",hex(entry),"exports",len(roots))
# entry-only recursive CFG, no call expansion
q=[entry]; seen=set(); ins={}; blocks={}
while q:
 st=q.pop()
 if st in seen or not is_exec(st):continue
 seen.add(st); seq=[]
 for x in dis(st,0x2000):
  a=x.address-0x400000; ins[a]=x; seq.append(x)
  m=x.mnemonic; ops=x.operands
  if m in ("ret","retn","iret","iretd","ud2","int3"):break
  if m=="call":
   nxt=a+x.size
   if is_exec(nxt) and nxt not in seen:q.append(nxt)
   continue
  if m.startswith("j"):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-0x400000
    if is_exec(t) and t not in seen:q.append(t)
   if m=="jmp":break
   continue
  nxt=a+x.size
  if is_exec(nxt) and nxt not in seen:q.append(nxt)
print("entry reachable instructions",len(ins),"starts",len(seen))
for t in (0x3667a,0x36691):print("target",hex(t),"in_entry_cfg",t in ins)

