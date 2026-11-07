import struct, math
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\mp_firingrange_zone.bin'; d=open(p,'rb').read()
for blob in [b'clip_player\x00clip_shot_block\x00clip_full\x00clip\x00', b'clip_player', b'clip_shot_block']:
 print('blob',blob)
 i=0;n=0
 while n<20:
  i=d.find(blob,i)
  if i<0: break
  print(hex(i),d[i-80:i+120].hex())
  i+=1;n+=1
