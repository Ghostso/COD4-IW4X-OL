import struct
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
for center in (0x3667a,0x36691):
 print('===',hex(center),'===')
 for st in range(center-64,center+8):
  # print only starts whose decode yields no invalid or privileged instruction in first 12 insns, up to 64 bytes
  from capstone import *
  md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=False
  ins=list(md.disasm(D[st:st+96],st))
  if not ins: continue
  bad=any(x.mnemonic in ('int','int1','int3','into','iret','iretd','hlt','in','out','ins','outs') for x in ins[:10])
  ends=any(x.mnemonic.startswith('ret') for x in ins[:16])
  if not bad and ends:
   print('candidate',hex(st),[(hex(x.address),x.bytes.hex(),x.mnemonic,x.op_str) for x in ins[:16]])
