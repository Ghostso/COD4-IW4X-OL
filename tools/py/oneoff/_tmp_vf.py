import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
files = sorted([f for f in os.listdir(D) if f.startswith('snap_') and f.endswith('.json')])
print('快照列表:', files)
def load(tag):
    img=open(os.path.join(D,tag+'.bin'),'rb').read()
    cov=open(os.path.join(D,tag+'_cover.bin'),'rb').read()
    return img,cov
def mk(img,cov):
    def rd(va,n):
        o=va-LO
        if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
        return img[o:o+n]
    def u32(va):
        b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
    return rd,u32
print()
print('=== ★ 修复验证: [0x82E1518] dwRoomMatchUber ===')
for tag in [f.replace('.json','') for f in files]:
    img,cov=load(tag)
    rd,u32=mk(img,cov)
    a=u32(0x082E1518)
    g=rd(0x0849B61C,1)
    b=u32(0x082E13FC)
    print('  %-10s dwRoomMatchUber=%-12s 开局标志=%s  dwRoomImp=%s' % (
        tag, ('0x%08X'%a) if a is not None else '未覆盖',
        (g[0] if g else '-'), ('0x%08X'%b) if b is not None else '-'))
