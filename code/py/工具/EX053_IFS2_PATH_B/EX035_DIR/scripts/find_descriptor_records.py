# -*- coding: utf-8 -*-
"""Read-only locator for 0x8000xxxx values and nearby printable names."""
import sys,os,struct,re,collections
U32=lambda b,o:struct.unpack_from('<I',b,o)[0]
def hx(x): return '0x%08X'%x
def parse(path):
 d=open(path,'rb').read(); e=U32(d,0x3c); c=e+4; n=struct.unpack_from('<H',d,c+2)[0]; osz=struct.unpack_from('<H',d,c+16)[0]; o=c+20; ib=U32(d,o+28); soi=U32(d,o+56); dd=o+96
 secs=[]
 for i in range(n):
  q=o+osz+i*40; secs.append((d[q:q+8].rstrip(b'\0').decode('latin1'),U32(d,q+12),U32(d,q+8),U32(d,q+20),U32(d,q+16)))
 return d,ib,soi,secs
def loc(secs,off):
 for i,(n,v,vs,r,rs) in enumerate(secs):
  if r<=off<r+rs:return i,v+off-r
 return -1,None
def main():
 d,ib,soi,secs=parse(sys.argv[1]); hits=[]
 for o in range(0,len(d)-3,4):
  v=U32(d,o)
  if 0x80000001<=v<=0x8000ffff:
   si,r=loc(secs,o); hits.append((o,r,si,v))
 print('aligned 0x80000001..0x8000FFFF count=%d'%len(hits))
 for o,r,si,v in hits:
  # nearby printable strings within 64 bytes, report candidate module/name strings
  lo=max(0,o-64); b=d[lo:o+96]
  ss=[]
  for m in re.finditer(rb'[A-Za-z0-9_.-]{4,64}',b):
   ss.append((lo+m.start()-o,m.group().decode('latin1')))
  before=U32(d,o-4) if o>=4 else None; after=U32(d,o+4) if o+8<=len(d) else None
  print('off=%s rva=%s sec=%d val=%s before=%s after=%s strings=%s'%(
   hx(o),hx(r) if r is not None else '-',si,hx(v),hx(before) if before is not None else '-',hx(after) if after is not None else '-',ss[:8]))
if __name__=='__main__':main()
