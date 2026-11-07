import struct, collections, pathlib
P=pathlib.Path(r'codoMP_client_shipRetail.exe'); D=P.read_bytes()
IB=0x400000; SOI=0x0E659000; rva0=0x8A8000; raw0=0x594000; rawsz=0x16E000
lo_va=0x00CA0000; hi_va=0x00D40000
def rd(va): return struct.unpack_from('<I',D,raw0+va-IB-rva0)[0]
def cls(v):
    if v==0:return 'Z'
    if IB<=v<IB+SOI:return 'P'
    if 0x80000000<=v<=0x8FFFFFFF:return 'S'
    if 1<=v<=0xFFFFFF:return 'N'
    return 'X'
vals=[rd(va) for va in range(lo_va,hi_va,4)]
print('category runs n>=3:')
s=0
for i in range(1,len(vals)+1):
    if i==len(vals) or cls(vals[i])!=cls(vals[s]):
        n=i-s
        if n>=3: print('%08X..%08X %s n=%4d first=%08X last=%08X'%(lo_va+4*s,lo_va+4*(i-1),cls(vals[s]),n,vals[s],vals[i-1]))
        s=i
print('\n0x1000-block summaries:')
for va in range(lo_va,hi_va,0x1000):
    cc=collections.Counter(cls(rd(x)) for x in range(va,va+0x1000,4))
    q=[(rd(x),rd(x+4)) for x in range(va,va+0x1000,8)]
    pz=sum(IB<=u<IB+SOI and v==0 for u,v in q)
    sz=sum(0x80000000<=u<=0x8fffffff and v==0 for u,v in q)
    print('%08X P=%3d Z=%3d S=%3d N=%2d X=%3d pz=%2d sz=%2d'%(va,cc['P'],cc['Z'],cc['S'],cc['N'],cc['X'],pz,sz))
