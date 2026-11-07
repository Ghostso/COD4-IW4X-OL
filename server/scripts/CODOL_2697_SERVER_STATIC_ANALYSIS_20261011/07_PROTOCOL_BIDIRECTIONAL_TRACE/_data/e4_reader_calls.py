import sys, os, struct, bisect
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
im=c.load(c.CLIENT_CAND)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# direct check of call encodings and target
for callr in [0xA2DC1,0xA2DEA,0x5AC1D0]:
 off=im.sec_of(callr); ptr=off[3]; va=off[1]; f=ptr+(callr-va)
 print('at',hex(callr),'file',hex(f),'bytes',im.data[f:f+8].hex())
 if im.data[f]==0xe8:
  rel=struct.unpack_from('<i',im.data,f+1)[0]; print(' e8 rel',hex(rel),'target',hex(callr+5+rel))
# list all raw E8 targets around known region manually
hits=[]
for off in range(0,len(im.data)-5):
 if im.data[off]==0xe8:
  sec=None
  for nm,va,vsz,ptr,rsz in im.sections:
   if rsz and ptr<=off<ptr+rsz:
    sec=(nm,va,ptr); break
  if not sec: continue
  nm,va,ptr=sec; src=va+(off-ptr); rel=struct.unpack_from('<i',im.data,off+1)[0]; tgt=src+5+rel
  if tgt in [0x5AC1D0,0x5ACB00,0xA2D90,0x63CB50,0x63C7F0,0x5B1F20]:
   hits.append((src,tgt))
print('manual target hits',[(hex(a),hex(b)) for a,b in hits])
print('\nFUNCTION 5AC1D0')
for ins in im.disasm(0x5AC1D0,count=80):
 print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
print('\nFUNCTION 5ACB00')
for ins in im.disasm(0x5ACB00,count=100):
 print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
# identify code functions with the exact +14/+18/+1c pattern
