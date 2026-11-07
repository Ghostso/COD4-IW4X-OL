import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read()
vals=[0x317c1ead,0x317d9c51,0x317c1f41,0x317c2507,0x300368cb]
for v in vals:
    print('\nval',hex(v))
    for base in [0,0x30000000,0x30c00000,0x30ce0000,0x31000000,0x32000000]:
        off=v-base
        if 0<=off<len(d):
            print(' base',hex(base),'off',hex(off),'bytes',d[off:off+32].hex(),'ascii',d[off:off+32])
