import sys, os, struct, bisect, json
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c, c_xref as x
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
im=c.load(c.CLIENT_CAND)
EXEC=[(va,va+rsz) for nm,va,vsz,ptr,rsz in im.sections if nm in ('.text','.tvm0')]
def in_exec(r): return any(a<=r<b for a,b in EXEC)
def va_of_file(off):
 for nm,va,vsz,ptr,rsz in im.sections:
  if rsz and ptr<=off<ptr+rsz: return nm,va+(off-ptr)
 return None,None
def file_of_rva(r):
 s=im.sec_of(r)
 if not s: return None
 nm,va,vsz,ptr,rsz=s
 return ptr+(r-va)
def dis(rva,n=80,start_adjust=0):
 print('\nDIS %X %s'%(rva,im.sec_of(rva)))
 for ins in im.disasm(rva,count=n):
  print(' %08x  %-12s %s'%(ins.address,ins.mnemonic,ins.op_str))
# calls with valid targets
calls={}
for nm,va,vsz,ptr,rsz in im.sections:
 if nm not in ('.text','.tvm0') or not rsz: continue
 for i in range(ptr,ptr+rsz-5):
  if im.data[i]==0xE8:
   rel=struct.unpack_from('<i',im.data,i+1)[0]
   src=va+(i-ptr); tgt=src+5+rel
   if in_exec(tgt): calls.setdefault(tgt,[]).append(src)
for t in [0xA2D90,0x5AC1D0,0x63CB50,0x63C7F0,0x5B1F20,0x5E94F0,0x636FC0,0x409640,0x404920,0x5EC7D0]:
 print('calls to %X: %s'%(t,[hex(v) for v in calls.get(t,[])]))
for off in [0x55c93,0xa1d94,0x8b2bb,0x930d84]:
 sec,r=va_of_file(off); print('xrefoff',hex(off),'sec',sec,'rva',hex(r) if r else None)
# raw bytes around A2D90
for r in [0xA2D70,0xA2D80,0xA2D90,0xA2DA0,0xA2DB0]:
 off=file_of_rva(r); print('bytes',hex(r),hex(off),im.data[off:off+64].hex())
# try dis from a few alignments
for r in [0xA2D60,0xA2D70,0xA2D80,0xA2D90,0xA2DA0,0xA2DB0]:
 dis(r,25)
