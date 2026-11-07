import struct,re
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
target=None
for i in range(n):
 t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
 if t!=28:continue
 b=d[off:off+sz]
 if b'SF_WEAPON_M4A1TECH_MP_NAME' in b: target=(i,off,sz,b);break
print('target',target[0],hex(target[1]),hex(target[2]))
b=target[3]
for val in [30,90,71,70,2100,2000,33,20,100,120,150,60,800,1600,3000]:
 hits=[j for j in range(0,len(b)-4,4) if struct.unpack_from('<i',b,j)[0]==val]
 print(val,[hex(x) for x in hits[:40]],len(hits))
# contiguous windows with many likely values
for o in range(0,min(len(b)-256,0x1000),4):
 vals=struct.unpack_from('<64i',b,o)
 score=sum(v in {30,90,71,70,2100,2000,33,20,100,120,150,60} for v in vals)
 if score>=5: print('window',hex(o),'score',score,vals[:32])
