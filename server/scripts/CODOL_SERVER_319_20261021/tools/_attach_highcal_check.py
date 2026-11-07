import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
for target in ['highcal_base','fmj_base']:
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
        if nm!=target: continue
        print(target,'count',cnt)
        pay=b[e+1:]
        for j in range(cnt):
            r=pay[j*12:(j+1)*12]
            print(j,r.hex(),'type',r[0],'flags',hex(struct.unpack_from('<H',r,2)[0]),'off',hex(struct.unpack_from('<I',r,4)[0]&0xffff),'val',hex(struct.unpack_from('<I',r,8)[0]))
        break
