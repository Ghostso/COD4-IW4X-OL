import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for va in [0xd391f0,0xd3927c,0xd39284,0xd3928c,0xd39510,0xd39570,0xdbc4ec]:
    o=va-0x400000
    e=d.find(b'\0',o)
    print(hex(va),repr(d[o:e].decode('latin1','replace')))
