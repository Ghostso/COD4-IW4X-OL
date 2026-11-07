p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); off=0x22c3666; A=0x28
print('old+0',d[off:off+64].hex())
print('new+0',d[off+A:off+A+64].hex())
for name,ad in [('old',off),('new',off+A)]:
 print(name,'+bfc',d[ad+0xbfc:ad+0xbfc+64].hex(),''.join(chr(x) if 32<=x<127 else '.' for x in d[ad+0xbfc:ad+0xbfc+64]))
 print(name,'+e90',d[ad+0xe90:ad+0xe90+32].hex())
print('search weapon sig',hex(d.find(b'SF_WEAPON_M4A1TECH_MP_NAME',off,off+0x11a2)))
