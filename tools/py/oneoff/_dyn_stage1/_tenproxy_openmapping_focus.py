from pathlib import Path
import pefile
from capstone import *
ROOT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p=ROOT/r"COD OL\TenProxy.dll"; d=p.read_bytes(); pe=pefile.PE(data=d,fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
def va2off(va):
 r=va-base
 for s in pe.sections:
  if s.VirtualAddress <= r < s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData): return s.PointerToRawData+r-s.VirtualAddress
def dump(lo,hi):
 for i in Cs(CS_ARCH_X86,CS_MODE_32).disasm(d[va2off(lo):va2off(hi)],lo): print("%08X %-24s %-8s %s"%(i.address,i.bytes.hex(),i.mnemonic,i.op_str))
print("--- 100060d0..10006230 ---"); dump(0x100060d0,0x10006230)
for va in [0x10023680,0x1002121c,0x10021198,0x10021118,0x10021094,0x10021018,0x10021234,0x100212a8,0x10020ef2,0x10020f70]:
 off=va2off(va)
 print("DATA",hex(va),"fileoff",hex(off),"bytes",d[off:off+96].hex())
 try:
  print(" UTF16",d[off:off+160].split(b'\0\0')[0].decode('utf-16le','replace'))
 except Exception as e: pass
