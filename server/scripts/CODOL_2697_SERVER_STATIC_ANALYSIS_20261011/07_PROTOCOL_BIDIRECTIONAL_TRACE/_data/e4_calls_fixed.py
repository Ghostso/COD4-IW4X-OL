import sys, os, struct, bisect, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
im=c.load(c.CLIENT_CAND)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# decode every executable section and map instruction by RVA
insns={}
for nm,va,vsz,ptr,rsz in im.sections:
 if nm not in ('.text','.tvm0') or not rsz: continue
 for ins in md.disasm(im.data[ptr:ptr+rsz], im.ib+va):
  insns[ins.address-im.ib]=ins
print('decoded',len(insns))
# list calls to correct absolute target, encoding target and caller
targets=[0x5AC1D0,0x5ACB00,0x63CB50,0x63C7F0,0x5B1F20,0x63CB50,0x5E94F0,0x636FC0,0x409640,0x404920,0x5EC7D0,0x5F11C0,0x63CB50]
for t in targets:
 arr=[]
 for base in [0x400000,0]:
  arr=[]
  for r,ins in insns.items():
   if ins.mnemonic=='call':
    try: d=int(ins.op_str,16)
    except: continue
    if d==base+t: arr.append(r)
  print('target base',hex(base),'rva',hex(t),'calls',[hex(x) for x in arr])
# exact caller of A2D90
for r,ins in insns.items():
 if ins.mnemonic=='call':
  try: d=int(ins.op_str,16)
  except: continue
  if d==im.ib+0xA2D90: print('A2D90 caller',hex(r))
# list caller site context around A2D90 call
cs=0xD9945FE
print('caller site',hex(cs))
for ins in im.disasm(cs-0x100,count=100): print(' %08x %-14s %s'%(ins.address,ins.mnemonic,ins.op_str))
