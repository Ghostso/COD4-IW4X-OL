import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for o in [0x23f819,0x23f81a,0x23f81b,0x23f81c,0x23f821,0x23f823,0x23f82b,0x23f83b,0x23f83c]:
 print(hex(o),d[o:o+16].hex())
