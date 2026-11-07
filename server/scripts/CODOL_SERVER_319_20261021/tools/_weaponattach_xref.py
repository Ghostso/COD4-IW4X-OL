import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for pat in [b'weaponattach\x00',b'weaponattach']:
 offs=[];i=0
 while len(offs)<50:
  i=d.find(pat,i)
  if i<0:break
  offs.append(i);i+=1
 print(pat,[hex(x) for x in offs])
 for off in offs[:20]:
  va=off+0x400000
  refs=[]
  needle=struct.pack('<I',va)
  j=0
  while len(refs)<20:
   j=d.find(needle,j)
   if j<0:break
   refs.append(j+0x400000);j+=1
  print(' va',hex(va),'refs',[hex(x) for x in refs])
