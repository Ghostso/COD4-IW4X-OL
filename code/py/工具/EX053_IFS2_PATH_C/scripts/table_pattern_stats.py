# -*- coding: utf-8 -*-
"""Read-only shape statistics for the full 512-DWORD table at 0xCA8000."""
import struct,math,collections,re
P=r'COD OL/codoMP_client_shipRetail.exe'; d=open(P,'rb').read(); off=0x594000; V=[struct.unpack_from('<I',d,off+4*i)[0] for i in range(512)]
inimg=lambda v:0x00400000<=v<0x0EA59000
def hx(x):return '0x%08X'%x
print('n=512 in_image=%d zero=%d sentinel=%d uniq=%d'%(sum(map(inimg,V)),V.count(0),sum(0x80000000<=v<=0x8fffffff for v in V),len(set(V))))
print('zero_indices='+' '.join(str(i) for i,v in enumerate(V) if v==0))
print('sentinel_indices='+' '.join(str(i) for i,v in enumerate(V) if 0x80000000<=v<=0x8fffffff))
# runs by category and arithmetic relationships
cats=[]
for v in V:
 c='IN' if inimg(v) else 'ZERO' if v==0 else 'SENT' if 0x80000000<=v<=0x8fffffff else 'OTHER'
 cats.append(c)
print('runs=',[(a,b,cats[a],b-a+1) for a,b in (lambda rs:[(rs[i][0],rs[i][-1]) for i in range(len(rs))])([])] if False else '')
runs=[]; s=0
for i in range(1,513):
 if i==512 or cats[i]!=cats[s]:
  runs.append((s,i-1,cats[s],i-s)); s=i
print('category_runs=%s'%runs)
# numeric deltas within each category; print exact descending/ascending runs >=3
def seqruns(pred,minn=3):
 out=[]; s=0
 for i in range(1,513):
  if i==512 or not pred(V[i-1],V[i]):
   if i-s>=minn:out.append((s,i-1,i-s))
   s=i
 return out
for name,pred in [('next=prev-16',lambda a,b:b==a-16),('next=prev+16',lambda a,b:b==a+16),('delta small even',lambda a,b:0<=b-a<=0x40 and (b-a)%2==0),('delta nonzero small even',lambda a,b:0<b-a<=0x40 and (b-a)%2==0)]:
 print(name,seqruns(pred,3))
# compare value ordering vs slot ordering for regions
print('\n[SELECTED REGION SEQUENCES]')
for lo,hi in [(0,52),(174,218),(219,344),(345,417),(418,474),(475,511)]:
 xs=V[lo:hi+1]; print('idx %d..%d n=%d min=%s max=%s asc_steps=%d desc_steps=%d equal=%d'%(lo,hi,len(xs),hx(min(xs)),hx(max(xs)),sum(b>a for a,b in zip(xs,xs[1:])),sum(b<a for a,b in zip(xs,xs[1:])),sum(b==a for a,b in zip(xs,xs[1:]))))
# target ranges by section and by low alignment
for name,rs in [('in',[v for v in V if inimg(v)]),('sent',[v for v in V if 0x80000000<=v<=0x8fffffff])]:
 if rs:print('%s values=%d min=%s max=%s'%(name,len(rs),hx(min(rs)),hx(max(rs))))
# infer if table is an array of fixed records: check 4-DWORD cells with sentinel/zero positions
print('\n[FIXED-4-DWORD CELL PATTERNS]')
pat=collections.Counter()
for i in range(0,512,4):
 c=tuple('IN' if inimg(v) else 'ZERO' if v==0 else 'SENT' if 0x80000000<=v<=0x8fffffff else 'OTHER' for v in V[i:i+4]);pat[c]+=1
print(pat)
# 2 dword
print('fixed-2',collections.Counter(tuple('IN' if inimg(v) else 'ZERO' if v==0 else 'SENT' if 0x80000000<=v<=0x8fffffff else 'OTHER' for v in V[i:i+2]) for i in range(0,512,2)))
