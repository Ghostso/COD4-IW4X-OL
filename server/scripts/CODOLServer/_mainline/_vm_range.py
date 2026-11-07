import struct, os, json
d=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_112143\engine'
b=open(os.path.join(d,'sentinel_table.bin'),'rb').read()
vals={}
for i in range(0,len(b),4):
    v=struct.unpack_from('<I',b,i)[0]
    if v: vals[0x00CA8000+i]=v
hi=[v for v in vals.values() if 0x10000000<=v<0x14000000]
lo=min(hi); hiA=max(hi)
print('image-base-range pointers: %d  min=%08x max=%08x span=%x' % (len(hi),lo,hiA,hiA-lo))
# page-align the region and estimate size
base=lo & ~0xFFF
top=(hiA+0x1000) & ~0xFFF
print('suggested dump base=%08x size=%x (%d bytes)' % (base, top-base, top-base))
# low pointers (0x00C90000 x535) -> these are inside the main module
low=[v for v in vals.values() if 0x00C00000<=v<0x00D00000]
print('in-module 0x00C9xxxx pointers: %d min=%08x max=%08x' % (len(low),min(low),max(low)))
# system dll pointers
sysp=[v for v in vals.values() if v>=0x60000000 and v<0x80000000]
print('system dll pointers: %d' % len(sysp))
for v in sorted(set(sysp))[:25]: print('   %08x' % v)
open(os.path.join(d,'..','sentinel_target_range.json'),'w').write(json.dumps({'base':base,'size':top-base,'min':lo,'max':hiA},indent=2))
print('OK')
