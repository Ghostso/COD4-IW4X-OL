import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
# dump direct pointers around known code/data tables and print xrefs to likely functions
for base in [0xe5c8c0,0xe5c978,0xe5ca30,0xe5cb00,0xe5c560]:
    print('\nTABLE',hex(base))
    for i in range(48):
        v=struct.unpack_from('<I',d,base-0x400000+4*i)[0]
        print(f'{i:02d}:{v:08x}',end=' ')
        if i%8==7: print()
