import struct, collections
from pathlib import Path
from capstone import *
from capstone.x86 import *
import pefile
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); IB=0x400000
peoff=struct.unpack_from("<I",D,0x3c)[0]; nsec=struct.unpack_from("<H",D,peoff+6)[0]; opt=peoff+24; so=opt+struct.unpack_from("<H",D,peoff+20)[0]
secs=[]
for i in range(nsec):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); ch=struct.unpack_from("<I",D,h+36)[0]; secs.append((i,nm,va,vs,rs,pr,ch))
def sec_for(r):
 for s in secs:
  if s[2] <= r < s[2]+s[3]: return s
 return None
def raw_for(r):
 s=sec_for(r)
 if not s or r<s[2] or r-s[2]>=s[4]: return None
 return s[5]+r-s[2]
def valid(r): return sec_for(r) is not None and sec_for(r)[1] != ".tvm0" and raw_for(r) is not None
md=Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
entry=struct.unpack_from("<I",D,opt+40)[0]
pel=pefile.PE("COD OL/codoMP_client_shipRetail.exe", fast_load=True); pel.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
roots=[entry]+[e.address for e in pel.DIRECTORY_ENTRY_EXPORT.symbols if e.address]
# Build instruction-level CFG from basic blocks. Stop a block on call: call has fallthrough only if it returns.
blocks={}; edges=collections.defaultdict(list); incoming=collections.defaultdict(list); call_edges=[]
q=collections.deque((r,None) for r in roots); seen_starts=set()
while q:
 st,parent=q.popleft()
 if st in seen_starts or not valid(st): continue
 seen_starts.add(st)
 o=raw_for(st); s=sec_for(st); lim=min(s[4]-(st-s[2]),0x10000)
 seq=list(md.disasm(D[o:o+lim],IB+st))
 if not seq: continue
 blocks[st]=seq
 for idx,x in enumerate(seq):
  r=x.address-IB; mn=x.mnemonic; ops=x.operands; nxt=r+x.size
  if mn.startswith("call"):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB; call_edges.append((r,t)); edges[r].append(("call",t)); incoming[t].append(("call",r))
    if valid(t): q.append((t,r))
   if valid(nxt):
    edges[r].append(("fall",nxt)); incoming[nxt].append(("fall",r)); q.append((nxt,r))
   break
  if mn.startswith("j"):
   if ops and ops[0].type==CS_OP_IMM:
    t=ops[0].imm-IB; edges[r].append(("branch",t)); incoming[t].append(("branch",r))
    if valid(t): q.append((t,r))
   if not mn.startswith("jmp") and valid(nxt):
    edges[r].append(("fall",nxt)); incoming[nxt].append(("fall",r)); q.append((nxt,r))
   break
  if mn.startswith("ret") or mn in ("iret","iretd","ud2","int3","hlt"):
   break
  if valid(nxt): q.append((nxt,r))
print("blocks",len(blocks),"instructions",sum(len(v) for v in blocks.values()),"call_edges",len(call_edges))
# Find predecessor instruction for each address if directly present.
for t in (0x36675,0x3667a,0x36680,0x36689,0x36691,0x36697,0x3669a,0x366dc):
 print("ADDR",hex(t),"incoming",[(typ,hex(a)) for typ,a in incoming.get(t,[])])
# Walk backward from 0x36675 through immediate predecessor edges recursively to roots.
for target in (0x36675,0x3667a,0x36691):
 print("=== BACKTRACE",hex(target),"===")
 # Find block address containing target
 owner=None
 for bs,seq in blocks.items():
  if any(x.address-IB == target for x in seq): owner=bs; break
 if owner is None:
  print("owner unknown"); continue
 print("owner",hex(owner))
 # reconstruct graph over block starts
 def block_targets(bs):
  seq=blocks[bs]; out=[]
  if not seq: return out
  # derive using last/instruction edges generally
  for x in seq:
   r=x.address-IB
   for typ,t in edges.get(r,[]): out.append((typ,t))
  return out
 # predecessor search over instructions
 rev=collections.defaultdict(list)
 for a,ts in edges.items():
  for typ,t in ts: rev[t].append((a,typ))
 qq=collections.deque([(target,None)]); seen=set(); found=None
 while qq and found is None:
  a,via=qq.popleft()
  if a in seen: continue
  seen.add(a)
  if a in roots: found=(a,via); break
  for pa,typ in rev.get(a,[]): qq.append((pa,a))
 print("nearest_root", None if found is None else (hex(found[0]),hex(found[1]) if found[1] else None))
# Dump all blocks that overlap the target interval.
print("blocks overlapping 36670..36700")
for bs,seq in blocks.items():
 a=seq[0].address-IB; b=seq[-1].address-IB+seq[-1].size
 if b>=0x36670 and a<0x36700:
  print("BLOCK",hex(a),hex(b))
  for x in seq: print(f" {x.address-IB:08X} {x.bytes.hex():<16} {x.mnemonic:<8} {x.op_str}")
