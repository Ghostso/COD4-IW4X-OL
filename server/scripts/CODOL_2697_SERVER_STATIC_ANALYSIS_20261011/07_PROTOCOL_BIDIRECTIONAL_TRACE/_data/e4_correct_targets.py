import sys, os, struct, bisect, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
im=c.load(c.CLIENT_CAND)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# correctly parse all executable sections into instruction map (linear disasm per section)
insns={}
for nm,va,vsz,ptr,rsz in im.sections:
 if nm not in ('.text','.tvm0') or not rsz: continue
 for ins in md.disasm(im.data[ptr:ptr+rsz], im.ib+va):
  insns[ins.address-im.ib]=ins
# collect direct calls and their normalized target rva
calls={}
for r,ins in insns.items():
 if ins.mnemonic!='call': continue
 try:
  if not ins.op_str.startswith('0x'): continue
  dest=int(ins.op_str,16)
 except: continue
 if im.ib <= dest < im.ib+0x40000000:
  t=dest-im.ib; calls.setdefault(t,[]).append(r)
for t in [0x1AC1D0,0x1ACB00,0x23CB50,0x23C7F0,0x5B1F20,0x5E94F0,0x636FC0,0x409640,0x404920,0x5EC7D0,0x5F11C0,0xA2D90]:
 print('ALIGNED CALLS %X'%t,[hex(x) for x in calls.get(t,[])])
# look for functions with msg cursor access; print candidate starts containing target fields
pats=[('esi',0x14,0x18,0x1c),('ecx',0x14,0x18,0x1c),('edi',0x14,0x18,0x1c)]
res=[]
for r,ins in insns.items():
 if r not in insns: continue
 # only consider nearby first 100 insns from this start as function candidate if prologue likely
 seq=[]; x=r
 for k in range(100):
  if x not in insns: break
  ins2=insns[x]; seq.append(ins2); x += ins2.size
 txt='; '.join(i.mnemonic+' '+i.op_str for i in seq)
 if ('[esi + 0x14]' in txt or '[ecx + 0x14]' in txt) and ('[esi + 0x18]' in txt or '[ecx + 0x18]' in txt) and ('[esi + 0x1c]' in txt or '[ecx + 0x1c]' in txt):
  res.append((r,txt[:600]))
print('CURSOR PATTERN candidate starts',len(res))
for r,t in res[:30]: print(hex(r),t)
# inspect A2D90 callers recursively
def callers(t): return calls.get(t,[])
def show_call_sites(targets, depth=2):
 seen=set(); frontier=list(targets)
 print('CALL GRAPH')
 for d in range(depth):
  nxt=[]
  for t in frontier:
   if t in seen: continue
   seen.add(t); cs=callers(t); print('depth',d,'target',hex(t),'callers',[hex(x) for x in cs])
   for x in cs:
    # find enclosing function-ish start: nearest int3 then prologue
    nxt.append(x)
  frontier=nxt
show_call_sites([0xA2D90],3)
# inspect caller context and functions around call sites
for cs in callers(0xA2D90):
 print('\nCALLER CONTEXT',hex(cs-0x120),hex(cs+0x120))
 for ins in im.disasm(max(0,cs-0x120), end_rva=cs+0x120,count=120): print(' %08x %-12s %s'%(ins.address,ins.mnemonic,ins.op_str))
