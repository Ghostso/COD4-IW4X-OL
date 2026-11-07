import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; targets={'scope_none','fmj_base','heartbeat_base'}
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=43: continue
    b=d[off:off+sz]; pos=b.find(b'\xff\xff\xff\xff')
    e=b.find(b'\0',pos+12) if pos>=0 else -1
    name=b[pos+12:e].decode('latin1') if e>=0 else ''
    if name in targets:
        print(name,hex(off),hex(sz),b.hex())
        print('after',b[e+1:].hex())
