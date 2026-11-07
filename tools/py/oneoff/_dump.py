import sys,struct
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes(); pe=struct.unpack_from("<I",D,0x3c)[0]; opt=pe+24; md=Cs(CS_ARCH_X86,CS_MODE_32)
for arg in sys.argv[1:]:
 a=int(arg,16); b=D[a:a+0x400]
 print("====",hex(a),"====")
 for x in md.disasm(b,0x400000+a):
  if x.address-0x400000>=a+0x300: break
  print(f"{x.address-0x400000:08X} {x.bytes.hex():<20} {x.mnemonic:<10} {x.op_str}")

