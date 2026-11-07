import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def cstr(va,n=100):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
rows=[]
for g in range(0x0849B700, 0x0849BC00, 4):
    p=u32(g)
    if not p: continue
    nm=cstr(u32(p) or 0, 40)
    if not nm: continue
    rows.append((nm,u32(p+4),u32(p+8),u32(p+0xC),p))
from collections import Counter
c=Counter(r[1] for r in rows)
print('=== dvar 标志 [+0x04] 分布 ===')
for fl,cnt in sorted(c.items()):
    print('  0x%08X  x%d' % (fl,cnt))
print()
print('=== 0x2000 组 (3291 所在) ===')
for nm,fl,t,v,p in rows:
    if fl==0x2000:
        print('  %-10s type=0x%-4X value=0x%08X' % (nm,t,v))
print()
print('=== 0x0 组里 dw_ 开头的 ===')
for nm,fl,t,v,p in rows:
    if fl==0 and nm.startswith('dw_'):
        print('  %-34s type=0x%-4X value=0x%08X' % (nm,t,v))
