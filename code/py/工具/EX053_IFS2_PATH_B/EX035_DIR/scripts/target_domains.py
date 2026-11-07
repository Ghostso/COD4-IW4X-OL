import struct,pathlib,collections
D=pathlib.Path(r'codoMP_client_shipRetail.exe').read_bytes(); raw0=0x594000; va0=0x8A8000; IB=0x400000; SOI=0x0E659000
rd=lambda va:struct.unpack_from('<I',D,raw0+va-IB-va0)[0]
vs=[(0xCA8000+4*i,rd(0xCA8000+4*i)) for i in range((0xCA93D0-0xCA8000)//4)]
ranges=[(0xA13000,0xA13000+0x1000),(0xA14000,0xA14000+0x1000),(0xA15000,0xA15000+0x400),(0xA15400,0xA15400+0x200),(0xA15500,0xA15500+0x100),(0xC95D00,0xC98000),(0xC98000,0xC9B800),(0xCA5500,0xCA5700)]
print('low2 all',collections.Counter(v&3 for _,v in vs if IB<=v<IB+SOI))
print('aligned odd slot relation',collections.Counter((i&1,v&3) for i,(_,v) in enumerate(vs) if IB<=v<IB+SOI))
for a,b in ranges:
 xs=[v for _,v in vs if a<=v<b]
 if xs:print('%08X..%08X n=%3d min=%08X max=%08X low2=%s'%(a,b,len(xs),min(xs),max(xs),dict(collections.Counter(v&3 for v in xs))))
# gaps between ranges
invs=[v for _,v in vs if IB<=v<IB+SOI]
print('\nvalue quartile counts')
for k in range(16):
 a=min(invs)+k*(max(invs)-min(invs)+1)//16; b=min(invs)+(k+1)*(max(invs)-min(invs)+1)//16
 print('%02X %08X..%08X %d'%(k,a,b,sum(a<=v<b for v in invs)))
