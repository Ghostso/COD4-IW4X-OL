import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for base in [0xe5cb80,0xe5cbc0,0xe5cc00,0xe5cc40,0xe5cc80,0xe5ccc0,0xe5cd00]:
    print('\n',hex(base))
    for i in range(24):
        v=struct.unpack_from('<I',d,base-0x400000+4*i)[0]
        print(f'{v:08x}',end=' ')
    print()
