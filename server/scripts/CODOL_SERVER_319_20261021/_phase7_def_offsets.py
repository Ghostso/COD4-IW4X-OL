import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for off in [0x23dba30,0x23dcacc,0x23e28eb]:
 for pos in [0,0xbf0,0xbfc,0xc00,0xc04,0x1000,0x1040]:
  print(hex(off),hex(pos),d[off+pos:off+pos+32].hex(),struct.unpack_from('<I',d,off+pos)[0] if pos+4<=len(d)-off else '')
 print()
