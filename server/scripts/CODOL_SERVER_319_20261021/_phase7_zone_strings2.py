import re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for lo,hi in [(0,0x3000),(0x240000,0x280000),(len(d)-0x200000,len(d))]:
 print('\nrange',hex(lo),hex(hi))
 for m in re.finditer(rb'[ -~]{5,}',d[lo:hi]):
  s=m.group().decode('ascii','replace')
  if any(x in s.lower() for x in ['weapon','m4','ak','mp5','cheytac','damage','fire','ammo','clip','reload']):
   print(hex(lo+m.start()),s[:240])
