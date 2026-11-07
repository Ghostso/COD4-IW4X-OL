import sys,os,struct,bisect
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
im=c.load(c.CLIENT_CAND);md=Cs(CS_ARCH_X86,CS_MODE_32);md.detail=True
# all calls to candidate funcs, and caller-containing functions determined by nearest int3/prologue
def find_starts(region_start=0x1000,region_end=0x7ada00):
 starts=[]
 for r in range(region_start,region_end):
  s=im.sec_of(r)
  if s and r+3<=s[1]+s[4]:
   b=im.read_rva(r,3)
   # use int3 padding before prologue: previous bytes int3 or ret, and current 55 8b ec or known no-ebp prologue
   if b==b'\x55\x8b\xec':
    if r<0x2000 or im.read_rva(r-1,1) in (b'\xcc',b'\xc3') or im.read_rva(r-2,2)==b'\xcc\xcc': starts.append(r)
 return starts
starts=find_starts()
print('candidate prologues',len(starts))
def nearest_start(x):
 a=[s for s in starts if s<=x]
 return a[-1] if a else None
# direct calls
raw=[]
for nm,va,vs,pt,rs in im.sections:
 if nm not in ('.text','.tvm0') or not rs: continue
 for i in range(pt,pt+rs-5):
  if im.data[i]==0xe8:
   src=va+(i-pt);rel=struct.unpack_from('<i',im.data,i+1)[0];dst=src+5+rel
   raw.append((src,dst))
for t in [0x1ac1d0,0x1acb00]:
 hits=[s for s,d in raw if d==t]
 print('\nTARGET',hex(t),'hits',len(hits))
 groups={}
 for s in hits: groups.setdefault(nearest_start(s),[]).append(s)
 for st,ss in sorted(groups.items()): print(' callerfunc',hex(st) if st else None,'sites',[hex(x) for x in ss])
# print clusters around sites in gamestate-related range 0x50000-0x120000
for t in [0x1ac1d0,0x1acb00]:
 hits=[s for s,d in raw if d==t and 0x50000<=s<0x120000]
 print('\nDETAILED',hex(t),len(hits))
 for s in hits[:25]:
  st=nearest_start(s)
  print(' site',hex(s),'func',hex(st) if st else '?')
  for ins in im.disasm(max(0,s-0x60), end_rva=s+0x80, count=60): print('   %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
