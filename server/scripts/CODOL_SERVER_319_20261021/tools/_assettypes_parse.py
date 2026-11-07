import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
def cstr(va):
    off=va-0x400000
    e=d.find(b'\0',off)
    return d[off:e].decode('latin1','replace') if 0<=off<len(d) and e>=0 else '<bad>'
for base in [0xe5c800,0xe5c8c0]:
    print('\nbase',hex(base))
    for i in range(64):
        v=struct.unpack_from('<I',d,base-0x400000+4*i)[0]
        if base==0xe5c800: print(i,hex(v),cstr(v))
        else: print(i,hex(v))
