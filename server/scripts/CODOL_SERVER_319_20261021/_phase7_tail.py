p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for i in [0x5ffc00,0x5ffd00,0x5ffd80,0x5ffe00,0x5ffec0,0x5fff00,0x5fff80,0x600000]:
 print('\n',hex(i),d[i:i+256].hex())
 print(''.join(chr(x) if 32<=x<127 else '.' for x in d[i:i+256]))
