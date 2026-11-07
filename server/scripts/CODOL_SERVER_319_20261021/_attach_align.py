import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'
d=open(p,'rb').read(); off=0x19c266c; b=d[off:off+0x45]
hits=[]; good=set(range(16))|{39}
for i in range(0,max(0,len(b)-47)):
    rows=[struct.unpack_from('<3I',b,i+12*j) for j in range(4)]
    if all(r[1] in good for r in rows): hits.append((i,rows))
print(hits[:30])
