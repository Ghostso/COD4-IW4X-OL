import struct
p=r'COD OL\codoMP_client_shipRetail.exe'
d=open(p,'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]; opt=e+24
ib=struct.unpack_from('<I',d,opt+28)[0]; dd=opt+96
secs=[]; nsec=struct.unpack_from('<H',d,e+6)[0]; so=opt+struct.unpack_from('<H',d,e+20)[0]
for i in range(nsec):
    o=so+i*40; nm=d[o:o+8].rstrip(b'\0').decode(); vs,va,rs,ra=struct.unpack_from('<IIII',d,o+8); secs.append((nm,va,vs,ra,rs))
def r2o(r):
    for nm,va,vs,ra,rs in secs:
        if va<=r<va+max(vs,rs): return ra+(r-vs) if False else ra+(r-va)
for nm,va,vs,ra,rs in secs: print(nm,hex(va),hex(vs),hex(ra),hex(rs))
ir,isz=struct.unpack_from('<II',d,dd+8)
print('import rva',hex(ir))
o=r2o(ir); print('off',hex(o))
i=0
while True:
    v=struct.unpack_from('<IIIII',d,o+i*20)
    print('desc',i,[hex(x) for x in v])
    if not any(v): break
    i+=1
    if i>5: break
