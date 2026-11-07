p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for s in [0xfc24,0x188f4,0x1f624,0x26da4]:
 print('\n',hex(s),d[s-128:s].hex())
