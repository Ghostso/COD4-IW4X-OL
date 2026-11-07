import struct
p=r'COD OL\codoMP_client_shipRetail.exe'
d=open(p,'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]; opt=e+24
ib=struct.unpack_from('<I',d,opt+28)[0]; dd=opt+96
for idx,nm in [(0,'export'),(1,'import'),(2,'resource'),(5,'reloc'),(9,'tls'),(12,'iat'),(13,'delay')]:
    r,s=struct.unpack_from('<II',d,dd+idx*8); print(nm,hex(r),hex(s))
print('--- import dir bytes')
ir,isz=struct.unpack_from('<II',d,dd+8)
secs=[]; nsec=struct.unpack_from('<H',d,e+6)[0]; so=opt+struct.unpack_from('<H',d,e+20)[0]
for i in range(nsec):
    o=so+i*40; vs,va,rs,ra=struct.unpack_from('<IIII',d,o+8); secs.append((va,vs,ra,rs))
def r2o(r):
    for va,vs,ra,rs in secs:
        if va<=r<va+max(vs,rs): return ra+(r-va)
o=r2o(ir)
print('import rva',hex(ir),'off',hex(o) if o else None)
if o:
    for i in range(0,isz,20):
        v=struct.unpack_from('<IIIII',d,o+i); print(' ',i,[hex(x) for x in v])
