import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[A+off:A+off+sz]
    if len(b)<12: continue
    nr,cnt,er=struct.unpack_from('<III',b,0)
    if nr!=0xffffffff: continue
    e=b.find(b'\0',12)
    if e<0: continue
    nm=b[12:e].decode('latin1','replace')
    if nm!='fmj_base': continue
    pay=b[e+1:]
    print('asset',hex(A+off),sz)
    print('header',b[:12].hex(),'name',nm,'pay',pay.hex())
    for j in range(cnt):
        r=pay[j*12:(j+1)*12]
        print(j,r.hex(),list(r))
