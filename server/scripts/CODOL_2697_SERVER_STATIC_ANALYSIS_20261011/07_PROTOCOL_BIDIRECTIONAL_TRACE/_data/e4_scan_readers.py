import sys,os,struct,bisect,re,hashlib,json
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
im=c.load(c.CLIENT_CAND)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
text_ptr=None
for nm,va,vsz,ptr,rsz in im.sections:
 if nm=='.text': text_ptr,text_va,text_rsz=ptr,va,rsz
# find instruction starts by linear scan
starts=[]; insns={}
for ins in md.disasm(im.data[text_ptr:text_ptr+text_rsz],im.ib+text_va):
 starts.append(ins.address-im.ib); insns[ins.address-im.ib]=ins
starts.sort()
# direct calls from all executable sections, linear scan only
calls={}
for nm,va,vsz,ptr,rsz in im.sections:
 if nm not in ('.text','.tvm0') or not rsz: continue
 for i in range(ptr,ptr+rsz-5):
  if im.data[i]==0xe8:
   rel=struct.unpack_from('<i',im.data,i+1)[0]; src=va+(i-ptr); tgt=src+5+rel
   calls.setdefault(tgt,[]).append(src)
for t in [0xA2D90,0x5AC1D0,0x5ACB00,0x63CB50,0x63C7F0,0x5B1F20,0x5E94F0,0x636FC0,0x409640,0x404920,0x5EC7D0,0x5F11C0,0x5F11C0]:
 print('CALLS',hex(t),[hex(x) for x in calls.get(t,[])])
# all code calls to 0x5ac1d0 from aligned instructions
for t in [0x5AC1D0,0x5ACB00,0x63CB50,0x63C7F0,0x5B1F20]:
 print('ALIGNED CALLS',hex(t))
 for ins in insns.values():
  if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
   try: dest=int(ins.op_str,16)-im.ib
   except: continue
   if dest==t: print(' ',hex(ins.address-im.ib))
# search immediate stack-size patterns
for size in [1,2,4]:
 patt=[]
 for r in starts:
  ins=insns[r]
  if ins.mnemonic=='push' and ins.op_str==hex(size) or (ins.mnemonic=='push' and ins.op_str==str(size)):
   patt.append(r)
 print('push count',size,len(patt),[hex(x) for x in patt[:20]])
# identify functions beginning with standard prologue and containing reader fields, produce concise list
cands=[]
for r,ins in list(insns.items()):
 if ins.mnemonic in ('push','mov') and r in insns:
  # start with int3 before or prologue
  prev=[x for x in starts if x<r][-1:] if any(x<r for x in starts) else []
  if ins.mnemonic=='push' and ins.op_str=='ebp':
   seq=[]
   for k in range(r,r+40):
    if k in insns: seq.append(insns[k])
   txt='; '.join(x.mnemonic+' '+x.op_str for x in seq)
   if ('esi + 0x14' in txt and 'esi + 0x18' in txt and 'esi + 0x1c' in txt) or ('ecx + 0x14' in txt and 'ecx + 0x18' in txt and 'ecx + 0x1c' in txt):
    cands.append((r,txt[:300]))
print('CURSOR PROLOGUE CANDIDATES',len(cands))
for r,t in cands: print(hex(r),t)
# show function around 0x5f1500 etc with starts
for r in [0x5F1500,0x5F15F0,0x5F11C0,0x5F0F00]:
 print('\nFUNC',hex(r))
 for ins in im.disasm(r,count=70): print(' %08x %-12s %s'%(ins.address,ins.mnemonic,ins.op_str))
