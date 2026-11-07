import struct,collections
p=r'..\run_codol_001\runs\PHASE7_STATIC_20261023\common_mp_zone.bin'; d=open(p,'rb').read(); N=len(d)
for start in [0xfc24,0x188f4,0x1f624,0x26da4]:
 i=0; good=0; last=0
 while start+16*(i+1)<=N:
  t,off,ptr,sz=struct.unpack_from('<4I',d,start+i*16)
  if not (t<64 and off<N and sz<N and off+sz<=N): break
  if i and off<last: break
  last=off;good+=1;i+=1
 print(hex(start),'good',good,'end',hex(start+good*16),'types',collections.Counter(struct.unpack_from('<I',d,start+16*j)[0] for j in range(good)))
