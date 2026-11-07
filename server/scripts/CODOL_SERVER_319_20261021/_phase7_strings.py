import re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read()
for pat in [b'clipmap',b'clipMap',b'CLIPMAP',b'brushsides',b'brush side',b'planes',b'cmodels',b'numBrushes',b'numBrushSides',b'ClipMaterial',b'CollisionAabbTree']:
 print('\n',pat)
 i=0; n=0
 while n<80:
  i=d.find(pat,i)
  if i<0: break
  va=i+0x400000
  s=d[max(0,i-50):min(len(d),i+len(pat)+80)]
  txt=''.join(chr(x) if 32<=x<127 else '.' for x in s)
  print(hex(va),hex(i),txt)
  i+=1; n+=1
