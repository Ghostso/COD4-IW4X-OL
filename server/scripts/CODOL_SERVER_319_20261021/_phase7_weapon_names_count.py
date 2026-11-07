import re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
# parse printable NUL strings starting at first weapon name
for start in [0x35371,0x35f2f,0x369bd,0x373f4,0x3820a]:
 vals=[];o=start
 while o<0x3a000 and len(vals)<600:
  e=d.find(b'\0',o)
  if e<0:break
  s=d[o:e]
  if not s: break
  if not re.fullmatch(rb'[A-Za-z0-9_*\-/ .]+',s): break
  vals.append(s.decode('latin1'));o=e+1
 print(hex(start),'count',len(vals),'first',vals[:8],'last',vals[-5:])
