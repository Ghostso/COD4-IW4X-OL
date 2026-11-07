import re,struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for off,sz in [(0x23dba30,0x109c),(0x23dcacc,0x116c),(0x23e28eb,0x1727)]:
 b=d[off:off+sz]; print('\n',hex(off),hex(sz))
 for m in re.finditer(rb'[ -~]{3,}',b): print(hex(m.start()),m.group().decode('latin1'))
 print('head',b[:64].hex())
