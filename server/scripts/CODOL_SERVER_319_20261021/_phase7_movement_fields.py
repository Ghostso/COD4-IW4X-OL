import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557
wanted={'m4':'SF_WEAPON_M4A1TECH_MP_NAME','ak':'SF_WEAPON_AK47_MP_NAME','r870':'SF_WEAPON_R870_MP_NAME','mp5':'SF_WEAPON_MP5K_MP_NAME'}
blobs={}
for k,w in wanted.items():
    for i in range(n):
        t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
        if t!=28: continue
        b=d[off:off+sz]
        if w.encode() in b:
            blobs[k]=b
            break
for name,o in [('move',0x9a0),('adsmove',0x9a4),('sprint',0x9a8),('adsIn',0x950),('adsOut',0x954),('overlay',0x694)]:
    print(name,hex(o))
    for k,b in blobs.items():
        raw=struct.unpack_from('<I',b,o)[0]
        f=struct.unpack_from('<f',b,o)[0]
        print(' ',k,hex(raw),round(f,6))
