import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for off,sz in [(0x23dba30,0x109c),(0x23dcacc,0x116c),(0x23e28eb,0x1727)]:
 b=d[off:off+sz]
 print('\n',hex(off))
 for pos in [0x670,0x674,0x678,0x694,0x6ec,0x6f0,0x6f4,0x6f8,0x6fc,0x700,0x714,0x718,0xbc8]:
  if pos+4<=len(b): print(hex(pos),struct.unpack_from('<f',b,pos)[0] if pos not in [0x694,0xbc8] else hex(struct.unpack_from('<I',b,pos)[0]))
