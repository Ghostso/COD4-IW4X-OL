import json,struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
count=0
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[A+off:A+off+sz]
    if len(b)<12: continue
    nr,cnt,er=struct.unpack_from('<III',b,0)
    if nr!=0xffffffff: continue
    e=b.find(b'\0',12); name=b[12:e].decode('latin1','replace'); pos=e+1
    for j in range(cnt):
        r=b[pos+j*12:pos+(j+1)*12]
        rt,idx,flags,raw,val=struct.unpack('<BBHII',r)
        if flags&1:
            lo=val&0xfffff
            print(name,j,'type',rt,'flags',hex(flags),'rawval',hex(val),'lo20',hex(lo))
            count+=1
            break
    if count>=30: break
