import struct, collections
from pathlib import Path
from capstone import *
from capstone.x86 import *
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; n=struct.unpack_from("<H",D,pe+6)[0]; opt=pe+24; so=opt+struct.unpack_from("<H",D,pe+20)[0]; secs=[]
for i in range(n):
 h=so+40*i; nm=D[h:h+8].split(b"\0")[0].decode("latin1"); vs,va,rs,pr=struct.unpack_from("<IIII",D,h+8); ch=struct.unpack_from("<I",D,h+36)[0]; secs.append((i,nm,va,vs,rs,pr,ch))
def sec(r):
 for s in secs:
  if s[2]<=r<s[2]+s[4]:return s
 return None
def off(r):
 s=sec(r); return None if not s else s[5]+r-s[2]
def u32(r):
 o=off(r); return None if o is None else struct.unpack_from("<I",D,o)[0]
def iscode(r):
 s=sec(r); return bool(s and s[1]!=".tvm0" and s[6]&0x20000000 and off(r) is not None)
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# Follow CFG from target instruction itself both forward and backward using decoded starts around it.
# Print every xref in .text-like sections to target or its containing bytes.
for target in (0x3667a,0x36691):
 print("TARGET",hex(target),"raw",D[target:target+12].hex())
 # all rel32 direct refs
 for i,nm,va,vs,rs,pr,ch in secs:
  if nm==".tvm0" or not rs:continue
  b=D[pr:pr+rs]
  for j in range(len(b)-5):
   a=va+j
   if b[j] in (0xe8,0xe9):
    t=a+5+struct.unpack_from("<i",b,j+1)[0]
    if t==target:print(" direct",hex(a))
# Extract the true-looking block by decoding from each known valid instruction start and show aligned candidates.
for st in (0x36640,0x36656,0x3665c,0x36675,0x36680,0x36697):
 print("START",hex(st))
 for x in md.disasm(D[st:st+40],0x400000+st):
  print(f" {x.address-0x400000:08X} {x.bytes.hex():<18} {x.mnemonic:<8} {x.op_str}")

