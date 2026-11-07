import struct
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'; d=open(p,'rb').read(); va=0xdb5cf0; off=va-0x400000
for o in range(off-0x200,off+0x200,16):
 vals=struct.unpack_from('<4I',d,o)
 txt=''.join(chr(x) if 32<=x<127 else '.' for x in d[o:o+16])
 print(f'{o+0x400000:08x} '+ ' '.join(f'{x:08x}' for x in vals)+'  '+txt)
