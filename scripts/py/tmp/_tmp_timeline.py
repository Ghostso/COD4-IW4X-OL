import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
def load(tag):
    return open(os.path.join(D,tag+'.bin'),'rb').read(), open(os.path.join(D,tag+'_cover.bin'),'rb').read()
def mk(img,cov):
    def rd(va,n):
        o=va-LO
        if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
        return img[o:o+n]
    def u32(va):
        b=rd(va,4)
        return struct.unpack('<I',b)[0] if b and len(b)==4 else None
    return rd,u32
U = 0x3ACA0CD8
print('=== 跨快照对比 dwRoomMatchUber 的状态字段 (看状态机有没有跑) ===')
print('  %-8s %-14s %-14s %-14s %-14s' % ('tag','[U+0x20]','[U+0x24]','[U+0x28]','[U+0x2C]'))
for tag in ('snap_002','snap_003','snap_004'):
    try:
        img,cov=load(tag)
    except Exception: continue
    rd,u32=mk(img,cov)
    vals=[u32(U+o) for o in (0x20,0x24,0x28,0x2C)]
    print('  %-8s %-14s %-14s %-14s %-14s' % (tag,
        *[('0x%08X'%v) if v is not None else '-' for v in vals]))
print()
print('=== 对比: 单例 dwRoomImp 是否也在 snap_002 就存在 ===')
for tag in ('snap_001','snap_002','snap_003','snap_004'):
    try: img,cov=load(tag)
    except Exception: continue
    rd,u32=mk(img,cov)
    a=u32(0x082E1518); b=u32(0x082E13FC); c=rd(0x0849B61C,1)
    print('  %-8s dwRoomMatchUber=%-12s dwRoomImp=%-12s 开局标志=%s' % (tag,
        ('0x%08X'%a) if a is not None else '-',
        ('0x%08X'%b) if b is not None else '-',
        c[0] if c else '-'))
