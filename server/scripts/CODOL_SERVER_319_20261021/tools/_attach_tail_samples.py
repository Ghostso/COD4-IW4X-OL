from pathlib import Path
import re,struct
p=Path(r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin')
d=p.read_bytes(); base=0xfc24;n=8557
# count printable-ish tails for type43; show hexdump and ASCII of several tails
shown=0
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=43: continue
 b=d[off:off+sz]
 for j in range(0,max(0,len(b)-11)):
  if b[j:j+4]==b'\xff'*4 and struct.unpack_from('<I',b,j+4)[0]<=64 and b[j+8:j+12]==b'\xff'*4:
   e=b.find(b'\0',j+12)
   if e>=0:
    nm=b[j+12:e].decode('latin1','replace')
    if nm and all(32<=ord(c)<127 for c in nm):
     tail=b[e+1:]
     print(f'{nm:24s} n={len(tail):4d} tail={tail[:96].hex()} ascii={"".join(chr(x) if 32<=x<127 else "." for x in tail[:96])}')
     shown+=1
     break
 if shown>=40: break
