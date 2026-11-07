import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read(); start=0x24008b
allowed={0,0x08010000,0x080028c0,0x08033240,0x08030200}
for n in range(1,200):
 o=start+n*24
 if o+4*n>len(d): break
 vals=[struct.unpack_from('<I',d,o+i*4)[0] for i in range(n)]
 good=sum(v in allowed for v in vals)
 if good>=n-1:
  print('candidate n',n,'off',hex(o),'good',good,'first',[hex(x) for x in vals[:12]])
