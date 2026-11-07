import re,os
root=r'D:\BaiduNetdiskDownload\使命召唤OL'
for p in [root+r'\_map_extract\mp_firingrange_zone.bin',root+r'\_map_extract\coop_train_zone.bin']:
 d=open(p,'rb').read(); print('\n',p,hex(len(d)))
 for pat in [b'm4a1',b'M4A1',b'weapon_m4a1',b'weapon_',b'damage',b'fireTime',b'penetration',b'ads',b'1156']:
  offs=[]; i=0
  while len(offs)<20:
   i=d.find(pat,i)
   if i<0: break
   offs.append(i);i+=1
  print(pat,[hex(x) for x in offs], 'count>=',len(offs))
