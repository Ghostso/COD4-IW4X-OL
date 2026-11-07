import struct,pathlib,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); IB=0x400000; raw0=0x594000; va0=0x8A8000; SOI=0x0E659000
def rd(va): return struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
def cls(v): return 'P' if IB<=v<IB+SOI else 'S' if 0x80000000<=v<=0x8fffffff else 'N' if 0<v<0x1000000 else 'Z' if v==0 else 'X'
# use a structural endpoint fixed by long all-zero run after 0xCA93CC, inspect candidate schemes
for a,b in [(0xCA8000,0xCA93D0),(0xCA876C,0xCA93D0),(0xCA8D10,0xCA93D0)]:
 print('\nREGION %08X..%08X size=%X dwords=%d'%(a,b,b-a,(b-a)//4))
 v=[rd(x) for x in range(a,b,4)]
 print('classes',collections.Counter(map(cls,v)))
 print('offsets mod4',collections.Counter((x>>2)%4 for x in range(a,b,4)))
 print('mod8 nonzero',collections.Counter(((x-a)//4)%2 for x in range(a,b,4) if rd(x)!=0))
 # sequence stride stats for pointer-only
 ptr=[rd(x) for x in range(a,b,4) if cls(rd(x))=='P']
 deltas=[y-x for x,y in zip(ptr,ptr[1:])]
 print('ptr delta top',collections.Counter(deltas).most_common(20))
 print('aligned dwords',sum(x%8==0 for x in range(a,b,4) if rd(x)!=0),'of',sum(rd(x)!=0 for x in range(a,b,4)))
print('\nfirst nonzero after 0xCA93D0 and runs')
for x in range(0xCA93D0,0xCA9A00,4):
 if rd(x): print('%08X %08X'%(x,rd(x)))
