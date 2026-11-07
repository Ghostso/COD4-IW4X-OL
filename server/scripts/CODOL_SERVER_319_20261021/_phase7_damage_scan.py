import struct
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); base=0xfc24;n=8557
wanted={'m4':'SF_WEAPON_M4A1TECH_MP_NAME','ak':'SF_WEAPON_AK47_MP_NAME','r870':'SF_WEAPON_R870_MP_NAME','mp5':'SF_WEAPON_MP5K_MP_NAME'}
blobs={}
for k,w in wanted.items():
 for i in range(n):
  t,off,ptr,sz=struct.unpack_from('<4I',d,base+i*16)
  if t!=28:continue
  b=d[off:off+sz]
  if w.encode() in b: blobs[k]=(off,sz,b);break
print({k:(hex(v[0]),hex(v[1])) for k,v in blobs.items()})
vals={'m4':{30,33,35,40,100},'ak':{40,45,49,50,100},'r870':{50,60,70,80,90,100},'mp5':{25,30,35,40,100}}
for o in range(0,min(len(v[2]) for v in blobs.values())-4,4):
 score=0
 ss=[]
 for k in wanted:
  x=struct.unpack_from('<i',blobs[k][2],o)[0]
  if x in vals[k]:score+=1
  ss.append(x)
 if score>=3: print(hex(o),ss)
