import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); base=0xfc24; n=8557; A=0x28
for i in range(n):
    t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
    if t!=28: continue
    b=d[A+off:A+off+sz]
    if b'SF_WEAPON_M4A1TECH_MP_NAME' in b:
        print('idx',i,'off',hex(off),'actual',hex(A+off),'size',hex(sz))
        for o in [0,4,8,0xe68,0xe70,0xd10,0xd14,0xd18,0xd1c,0xd28,0xd30,0x9a0,0x9a4,0x9a8,0xd4c,0xd7c,0x884,0x890,0x898]:
            if o+4<=len(b): print(hex(o),hex(struct.unpack_from('<I',b,o)[0]),struct.unpack_from('<i',b,o)[0],round(struct.unpack_from('<f',b,o)[0],6))
        break
