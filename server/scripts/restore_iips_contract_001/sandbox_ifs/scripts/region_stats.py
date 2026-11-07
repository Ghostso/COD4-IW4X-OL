import pathlib,struct,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
# entropy and simple structural stats for regions
import math
def ent(b):
 c=collections.Counter(b);n=len(b);return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0
for a,b in [(0xCA8000,0xCA8768),(0xCA8000,0xCA8800),(0xCA876C,0xCA93D0),(0xCA8780,0xCA8CC8),(0xCA8D10,0xCA93D0)]:
 o=raw0+(a-IB-va0); bb=D[o:o+(b-a)]
 print('%08X..%08X size=%X ent=%.3f zero_bytes=%d ptr_dwords=%d sentinel=%d uniq=%d'%(a,b,len(bb),ent(bb),bb.count(0),sum(IB<=rd(x)<0xEA59000 for x in range(a,b,4)),sum(0x80000000<=rd(x)<=0x8fffffff for x in range(a,b,4)),len(set(rd(x) for x in range(a,b,4)))))
