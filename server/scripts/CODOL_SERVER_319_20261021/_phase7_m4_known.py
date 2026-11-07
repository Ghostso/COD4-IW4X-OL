import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); b=d[0x22c3666:0x22c3666+0x11a2]
for name,o in [('iStartAmmo',0x55c),('iMaxAmmo',0x574),('iClipSize',0xb60),('shotCount',0x578),('iFireTime',0xb68),('iFireDelay',0x59c),('iReloadTime',0x5c8),('iReloadEmpty',0x5d4),('iReloadAdd',0x5dc),('iReloadStart',0x5ec),('iReloadStartAdd',0x5f0),('iReloadEnd',0x5f4),('adsIn',0x950),('adsOut',0x954),('move',0x670),('adsMove',0x674),('sprint',0x678)]:
 print(name,hex(o),struct.unpack_from('<i',b,o)[0],hex(struct.unpack_from('<I',b,o)[0]))
