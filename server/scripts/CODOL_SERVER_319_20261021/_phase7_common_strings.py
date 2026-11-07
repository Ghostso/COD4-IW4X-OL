import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read()
for pat in [b'm4a1tech',b'ak47',b'r870',b'cheytac',b'weapon_m4',b'SF_WEAPON_M4']:
 offs=[];i=0
 while len(offs)<100:
  i=d.find(pat,i)
  if i<0:break
  offs.append(i);i+=1
 print(pat,len(offs),[hex(x) for x in offs[:40]])
