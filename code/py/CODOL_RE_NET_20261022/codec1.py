import struct
d=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B=0x400000
for off in range(0xDA45C0,0xDA4700,4):
    o=off-B
    a=struct.unpack_from('<I',d[o:o+4])[0]
    print('%X : %X'%(off,a))