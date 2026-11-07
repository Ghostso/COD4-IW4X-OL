import struct
from pathlib import Path
D=Path("COD OL/codoMP_client_shipRetail.exe").read_bytes()
for pat,name in ((b"\x55\x8b\xec","push_ebp_mov_ebp_esp"),(b"\x55\x89\xe5","push_ebp_mov_esp_ebp"),(b"\x8b\xff\x55\x8b\xec","hotpatch"),(b"\x53\x56\x57","push_regs")):
 print(name)
 pos=0
 while True:
  i=D.find(pat,pos)
  if i<0: break
  if 0x35000<=i<0x36800: print(hex(i))
  pos=i+1

