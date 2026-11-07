import struct,collections,csv
from capstone import *
d=open(r"codoMP_client_shipRetail.exe","rb").read(); IB=0x400000
sh=struct.unpack_from("<I",d,0x3c)[0]; n=struct.unpack_from("<H",d,sh+6)[0]; opt=sh+24; oh=struct.unpack_from("<H",d,sh+20)[0]; o=opt+oh
secs=[]
for i in range(n):
 h=o+40*i; name=d[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",d,h+8); secs.append(dict(i=i,name=name,va=va,vs=vs,rs=rs,pr=pr,ch=struct.unpack_from("<I",d,h+36)[0]))
def sec(rva):
 for s in secs:
  if s["va"]<=rva<s["va"]+max(s["vs"],s["rs"]):return s
 return None
def off(rva):
 s=sec(rva)
 if not s:return None
 q=rva-s["va"]
 return s["pr"]+q if 0<=q<s["rs"] else None
def rd32(rva):
 f=off(rva);return None if f is None else struct.unpack_from("<I",d,f)[0]
def is_exec(rva):
 s=sec(rva);return bool(s and s["name"]!=".tvm0" and s["ch"]&0x20000000 and off(rva) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# roots same clean export+entry set
optbase=opt;dd=optbase+96;exp_rva,exp_sz=struct.unpack_from("<II",d,dd)
def u32(rva):return struct.unpack_from("<I",d,off(rva))[0]
nf=u32(exp_rva+24);af=u32(exp_rva+28);roots=[0xe5dc690]
for i in range(nf):
 r=u32(af+4*i)
 if r and is_exec(r):roots.append(r)
roots=sorted(set(roots))
# recursive reachable starts by direct calls/jumps/fallthrough, stop at indirect and returns.
seen=set(); q=collections.deque(roots); insmap={}
def decode(start):
 f=off(start)
 if f is None:return []
 s=sec(start); end=min(s["vs"],s["rs"]); return list(md.disasm(d[f:f+min(0x400,end-(start-s["va"]))],IB+start))
while q:
 st=q.popleft()
 if st in seen or not is_exec(st):continue
 seen.add(st)
 for x in decode(st):
  insmap[x.address-IB]=x
  m=x.mnemonic
  if m in ("ret","retn","iret","iretd","ud2","int3"):break
  if m=="call":
   if x.operands and x.operands[0].type==CS_OP_IMM:
    t=x.operands[0].imm-IB
    if is_exec(t):q.append(t)
   continue
  if m.startswith("j"):
   if x.operands and x.operands[0].type==CS_OP_IMM:
    t=x.operands[0].imm-IB
    if is_exec(t):q.append(t)
   if m=="jmp":break
print("ROOTS",len(roots),"REACHED_STARTS",len(seen),"INS",len(insmap))
# all raw refs to target slots, report group flags
slots=[0xca8114,0xca8194,0xca812c,0xca819c,0xca8164]
for slot in slots:
 print("=== SLOT %08X VALUE %08X"%(slot,rd32(slot-IB)))
 rows=[]
 for s in secs:
  if s["name"]==".tvm0":continue
  b=d[s["pr"]:s["pr"]+s["rs"]]
  for j in range(len(b)-6):
   if b[j]==0xff and b[j+1] in (0x15,0x25) and struct.unpack_from("<I",b,j+2)[0]==slot:
    rva=s["va"]+j; x=insmap.get(rva); z=next(md.disasm(d[off(rva):off(rva)+15],IB+rva,count=1),None)
    rows.append((rva,x,z,s))
 print("count",len(rows),"reachable_instruction_start",sum(x is not None for rva,x,z,s in rows),"self_boundary",sum(z is not None for rva,x,z,s in rows),"candidate_code_section",sum(is_exec(rva) for rva,x,z,s in rows))
 for rva,x,z,s in rows[:8]:
  print("REF %08X sec=%s exec=%s self=%s reach=%s"%(rva,s["name"],is_exec(rva),z.bytes.hex() if z else "-",x.bytes.hex() if x else "-"))
