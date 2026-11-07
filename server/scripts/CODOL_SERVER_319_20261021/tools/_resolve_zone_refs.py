p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read()
vals=[0x3003737d,0x300368cb,0x317c1ead,0x317d9c51,0x3180adf0]
for v in vals:
    print('\n',hex(v))
    for base in [0,0x28,0x30000000,0x30000028,0x31000000,0x31000028,0x30c00000,0x30ce0000]:
        off=v-base
        if 0<=off<len(d):
            s=d[off:off+80]
            txt=''.join(chr(x) if 32<=x<127 else '.' for x in s)
            print(hex(base),hex(off),txt[:80])
