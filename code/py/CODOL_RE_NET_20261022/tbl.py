import struct
d=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B=0x400000
for name,va,n in [('entityState',0xDA63E8,24),('struct3',0xDA90A8,9)]:
    print('=== %s @ 0x%X entries=%d ==='%(name,va,n))
    o=va-B
    for i in range(n):
        p=o+i*12
        off=struct.unpack_from('<I',d[p:p+4])[0]
        bits=struct.unpack_from('<i',d[p+4:p+8])[0]
        print('  [%2d] offset=0x%03X bits=%d'%(i,off,bits))