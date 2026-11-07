import re,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine\engine_best.bin'
b=open(p,'rb').read(); base=0x994000
def dump(lo,hi):
    s=max(0,lo-base); e=min(len(b),hi-base)
    print('\n===== %08x..%08x ====='%(lo,hi))
    for m in re.finditer(rb'[\x20-\x7e]{4,}',b[s:e]):
        va=base+s+m.start(); text=m.group().decode('ascii','replace')
        print('%08x %s'%(va,text))
# key regions
for lo,hi in [(0x00DC7000,0x00DC7600),(0x00DC9000,0x00DCA000),(0x00DBF800,0x00DC0200),(0x00DDE000,0x00DE0300),(0x00E43F00,0x00E49600),(0x00DBD400,0x00DBD800)]:
    dump(lo,hi)
