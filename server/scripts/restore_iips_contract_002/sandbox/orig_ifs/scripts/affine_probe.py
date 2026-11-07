import struct,pathlib,collections,statistics
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; SOI=0x0E659000; raw0=0x594000; va0=0x8A8000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
a=0xCA8000; b=0xCA93D0
vs=[rd(x) for x in range(a,b,4)]
uv=sorted(set(vs))
print('N',len(vs),'unique',len(uv),'min',hex(min(vs)),'max',hex(max(vs)))
# exact affine relation v = m*i+c for slot-relative / absolute index, solve candidates
pairs=[]
for i,v in enumerate(vs):
 if IB<=v<IB+SOI: pairs.append((i,v))
for use in ('i','addr','target-index'):
 d=[]
 for i,v in pairs:
  x=i if use=='i' else (a+4*i) if use=='addr' else (v>>2)
  d.append(v-4*x)
 print(use,'most common constants',collections.Counter(d).most_common(10))
# occurrence counts in region
co=collections.Counter(vs)
print('most common values',[(hex(k),n) for k,n in co.most_common(30)])
print('duplicates',sum(1 for n in co.values() if n>1))
# show exact first non-16 delta locations in long sequence
for lo,hi in [(0xCA876C,0xCA93D0),(0xCA8780,0xCA8CC8),(0xCA8D10,0xCA93D0)]:
 print('\nRUN',hex(lo),hex(hi))
 last=None
 for x in range(lo,hi,4):
  v=rd(x)
  if last is not None and v!=0 and last!=0 and v-last!=16:
   print(' %08X %08X delta=%d prev=%08X'%(x,v,v-last,last))
  last=v if v else last
