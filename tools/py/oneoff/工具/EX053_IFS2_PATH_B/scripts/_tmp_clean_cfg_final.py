import struct,collections
from capstone import *
d=open(r"codoMP_client_shipRetail.exe","rb").read(); IB=0x400000
sh=struct.unpack_from("<I",d,0x3c)[0]; n=struct.unpack_from("<H",d,sh+6)[0]; opt=sh+24; oh=struct.unpack_from("<H",d,sh+20)[0]; o=opt+oh
secs=[]
for i in range(n):
 h=o+40*i; name=d[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",d,h+8); secs.append((name,va,vs,rs,pr))
def off(rva):
 for t,va,vs,rs,pr in secs:
  if va<=rva<va+min(vs,rs): return pr+rva-va
 return None
def in_code(rva):
 return any(t==".tp3" and va<=rva<va+vs for t,va,vs,rs,pr in secs)
# roots: entry + EAT code/data addresses that actually point into code sections; direct root extraction from export dir
optbase=opt; dd=optbase+96
exp_rva,exp_sz=struct.unpack_from("<II",d,dd)
def u32(r): return struct.unpack_from("<I",d,off(r))[0]
def u16(r): return struct.unpack_from("<H",d,off(r))[0]
nf=u32(exp_rva+24); af=u32(exp_rva+28); roots=[0xe5dc690]
for i in range(nf):
 r=u32(af+4*i)
 if r and in_code(r): roots.append(r)
roots=sorted(set(roots))
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
seen=set(); starts=set(); ins=0; q=collections.deque(roots)
def decode(start):
 f=off(start)
 if f is None:return []
 # stop at chunk end or next non-code gap
 fr=min([va+min(vs,rs) for t,va,vs,rs,pr in secs if t==".tp3" and va<=start<va+min(vs,rs)] or [start])
 return list(md.disasm(d[f:f+min(0x1000,fr-start)],IB+start))
while q:
 start=q.popleft()
 if start in seen or not in_code(start):continue
 seen.add(start)
 for x in decode(start):
  starts.add(x.address-IB); ins+=1
  m=x.mnemonic
  # stop at first control transfer to avoid falling through into unrelated data in one chunk
  if m in ("ret","retn","iret","iretd","int3","ud2"): break
  if m=="call":
   if x.operands and x.operands[0].type==CS_OP_IMM:
    t=x.operands[0].imm-IB
    if in_code(t):q.append(t)
   continue
  if m.startswith("j"):
   if x.operands and x.operands[0].type==CS_OP_IMM:
    t=x.operands[0].imm-IB
    if in_code(t):q.append(t)
   if m=="jmp":break
   # conditional: continue fallthrough
print("roots",len(roots),[hex(x) for x in roots[:25]])
print("starts",len(starts),"decoded_instructions_from_all_starts",ins,"functions",len(seen))
table=[]
for st in sorted(starts):
 f=off(st)
 if f is None:continue
 for x in md.disasm(d[f:f+16],IB+st):
  if x.bytes[:2] in (b"\xff\x15",b"\xff\x25"):
   op=struct.unpack_from("<I",x.bytes,2)[0]
   if 0xca8000<=op<0xca8800: table.append((st,op,x.mnemonic,x.op_str))
  break
print("table_refs",len(table))
for x in table:print("%08X %08X %s %s"%(x[0],x[1],x[2],x[3]))
