import struct, collections
from pathlib import Path
from capstone import *
from capstone.x86 import *
import pefile
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); IB=0x400000
peoff=struct.unpack_from("<I",D,0x3c)[0]; nsec=struct.unpack_from("<H",D,peoff+6)[0]; opt=peoff+24; so=opt+struct.unpack_from("<H",D,peoff+20)[0]
secs=[]
for i in range(nsec):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); ch=struct.unpack_from("<I",D,h+36)[0]; secs.append(dict(i=i,nm=nm,va=va,vs=vs,rs=rs,pr=pr,ch=ch))
def sec_for(r):
 for s in secs:
  if s["va"] <= r < s["va"]+s["vs"]: return s
 return None
def raw_for(r):
 s=sec_for(r)
 if not s or r<s["va"] or r-s["va"]>=s["rs"]: return None
 o=s["pr"]+r-s["va"]
 return o if 0<=o<len(D) else None
def exec_valid(r):
 s=sec_for(r); return bool(s and s["nm"]!=".tvm0" and (s["ch"] & 0x20000000) and raw_for(r) is not None)
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
entry=struct.unpack_from("<I",D,opt+40)[0]
pel=pefile.PE("COD OL/codoMP_client_shipRetail.exe", fast_load=True)
pel.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
exports=[e.address for e in pel.DIRECTORY_ENTRY_EXPORT.symbols if e.address]
roots=sorted(set([entry]+exports))
print("roots",len(roots),"entry",hex(entry),"exports",len(exports))
starts=collections.deque(roots); seen_starts=set(); insmap={}; preds=collections.defaultdict(set); calls=[]
while starts:
 st=starts.popleft()
 if st in seen_starts or not exec_valid(st): continue
 seen_starts.add(st)
 o=raw_for(st); s=sec_for(st); lim=min(s["rs"]-(st-s["va"]),0x10000)
 for x in md.disasm(D[o:o+lim],IB+st):
  r=x.address-IB; insmap[r]=x
  mn=x.mnemonic; ops=x.operands; nxt=r+x.size
  if mn.startswith("call"):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB; calls.append((r,t))
    if exec_valid(t): starts.append(t)
   if exec_valid(nxt): starts.append(nxt)
   continue
  if mn.startswith("j"):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB; preds[t].add(r)
    if exec_valid(t): starts.append(t)
   if not mn.startswith("jmp") and exec_valid(nxt): starts.append(nxt)
   continue
  if mn.startswith("ret") or mn in ("iret","iretd","ud2","int3","hlt"): break
  if exec_valid(nxt): starts.append(nxt)
print("reached instructions",len(insmap),"starts",len(seen_starts),"calls",len(calls))
for t in (0x365e0,0x364f0,0x36510,0x36520,0x36570,0x36670,0x36675,0x3667a,0x36680,0x36689,0x36691,0x36697,0x36790):
 print("TARGET",hex(t),"is_start",t in seen_starts,"in_insmap",t in insmap,"preds",[hex(x) for x in sorted(preds.get(t,[]))])
print("direct callers to local range")
for a,t in sorted(calls):
 if 0x36500<=t<0x36800: print(hex(a),"->",hex(t))
