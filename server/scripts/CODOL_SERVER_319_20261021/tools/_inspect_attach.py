import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24;n=8557
cnt=0
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t==43:
        b=d[off:off+sz]
        print('index',i,'off',hex(off),'size',hex(sz),'head',b[:64].hex())
        print('strings', ''.join(chr(x) if 32<=x<127 else '.' for x in b[:128]))
        cnt+=1
        if cnt>=12: break
print('shown',cnt)
