import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
for target in ['quickdraw_base','fmj_base','highcal_base','flashhider_base','scope_none','silencer_m4','akimbo_base','heartbeat_base']:
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
        pay=b[e+1:]
        print('\n'+target,'count',cnt,'paylen',len(pay))
        for j in range(cnt):
            r=pay[j*12:(j+1)*12]
            if len(r)<12: break
            typ,idx,unk=struct.unpack_from('<BBH',r,0)
            raw_off=struct.unpack_from('<I',r,4)[0]
            val=struct.unpack_from('<I',r,8)[0]
            print(j,'type',typ,'idx',idx,'unk',hex(unk),'raw_off',hex(raw_off),'off_low',hex(raw_off&0xffff),'off_hi',hex(raw_off>>16),'val',hex(val))
        break
