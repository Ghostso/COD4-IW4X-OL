p=r'D:\BaiduNetdiskDownload\使命召唤OL\_map_extract\coop_train_zone.bin'; d=open(p,'rb').read()
for o in range(0x23ff30,0x240180,16): print('%08x %s'%(o,d[o:o+16].hex()))
