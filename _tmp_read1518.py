import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
def load(tag):
    img=open(os.path.join(D,tag+'.bin'),'rb').read()
    cov=open(os.path.join(D,tag+'_cover.bin'),'rb').read()
    return img,cov
img,cov = load('snap_003')
print('snap_003 覆盖 %.1f MB' % (sum(cov)/1048576))
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img): return None
    if sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
print()
print('=== ★ 目标: [0x82E1518] (dwRoomMatchUber) ===')
for va,label in ((0x082E1518,'dwRoomMatchUber'),(0x082E1514,'?'),(0x082E13FC,'dwRoomImp'),
                 (0x08269774,'大厅连接对象槽'),(0x0849B61C,'已请求开局标志')):
    v=u32(va)
    print('  [0x%08X] %-18s = %s' % (va,label, ('0x%08X (%d)'%(v,v)) if v is not None else '未覆盖'))
print()
print('=== dwRoomImp 实例确认 ===')
p=u32(0x082E13FC)
if p:
    vt=u32(p)
    print('  单例 0x%08X vtable=0x%08X' % (p,vt))
    g=rd(p+0x10614,1)
    print('  闸门B [+0x10614] = %s' % (g[0] if g else '未覆盖'))
