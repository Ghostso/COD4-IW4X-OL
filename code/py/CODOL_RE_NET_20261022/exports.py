import struct
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]; opt=e+24
ib=struct.unpack_from('<I',d,opt+28)[0]; dd=opt+96
erva,esz=struct.unpack_from('<II',d,dd)
secs=[]; nsec=struct.unpack_from('<H',d,e+6)[0]; so=opt+struct.unpack_from('<H',d,e+20)[0]
for i in range(nsec):
    o=so+i*40; vs,va,rs,ra=struct.unpack_from('<IIII',d,o+8); secs.append((va,vs,ra,rs))
def r2o(r):
    for va,vs,ra,rs in secs:
        if va<=r<va+max(vs,rs): return ra+(r-va)
eo=r2o(erva)
vals=struct.unpack_from('<IIHHIIIIII',d,eo)
print('export dir fields:',[hex(x) for x in vals])
nsig,ntime,nmaj,nmin,ndll,nameRVA,ordbase,nfunc,nname,af,an,ao=struct.unpack_from('<IIHHIIIIIII',d,eo)
print('nfunc',nfunc,'nname',nname)
print('dllname',d[r2o(nameRVA):d.find(b"\0",r2o(nameRVA))])
for i in range(nfunc):
    rva=struct.unpack_from('<I',d,r2o(af)+4*i)[0]
    print('  func[%d] RVA=%#010x VA=%#010x'%(i,rva,ib+rva))
for i in range(nname):
    nr=struct.unpack_from('<I',d,r2o(an)+4*i)[0]; o=r2o(nr); nm=d[o:d.find(b'\0',o)].decode('latin1'); print('  name[%d]=%r'%(i,nm))
for i in range(nfunc):
    ordv=struct.unpack_from('<H',d,r2o(ao)+2*i)[0]; print('  ord[%d]=%d'%(i,ordbase+ordv))
# also list import by ordinal from exe perspective
