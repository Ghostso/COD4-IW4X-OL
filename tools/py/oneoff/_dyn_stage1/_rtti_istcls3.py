from pathlib import Path
import pefile,struct
from capstone import *
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
p=ROOT/r'COD OL\codoMP_client_shipRetail.exe'; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+r-s.VirtualAddress
 raise ValueError(hex(va))
def q(va,n): return struct.unpack_from('<'+'I'*n,d,va2off(va))
def dump(lo,hi):
 for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[va2off(lo):va2off(hi)],lo):
  print('%08X %-24s %-8s %s'%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
for va in [0xE05D40,0xE05D80,0xE05DC0,0xE05DE0,0xE05E00,0xDF7F48,0xDF8048,0xDF8010,0xE06960,0xE06980]:
 try: print('\nQ',hex(va),[hex(x) for x in q(va,24)])
 except Exception as e: print('fail',hex(va),e)
for va in [0xE05D60,0xE05DC0,0xE05DE0,0xDF7F60,0xDF8060]:
 try: print('\nDUMPDATA',hex(va),d[va2off(va):va2off(va)+160].hex())
 except Exception as e: print(e)
for vt in [0xDF7F68,0xDF8068,0xDF8034]:
 try:
  vals=q(vt,16); print('\nVT',hex(vt),[hex(x) for x in vals])
  for j,v in enumerate(vals):
   if 0x401000<=v<0xca8000:
    print(' METHOD',j,hex(v)); dump(v,min(0x100,0xca8000-v))
 except Exception as e: print('vt fail',hex(vt),e)
