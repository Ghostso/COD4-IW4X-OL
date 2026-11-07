p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in [0x826,0xc6a,0x21e7,0x24c4,0x2657d,0x6aef6,0x5ffefe]:
 print('\n',hex(i),d[max(0,i-80):i+180].hex())
 print(''.join(chr(x) if 32<=x<127 else '.' for x in d[max(0,i-80):i+180]))
