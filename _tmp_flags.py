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
print('=== 全 dvar 表按 [+0x04] 标志分组 ===')
rows=[]
for g in range(0x0849B700, 0x0849BC00, 4):
    p=u32(g)
    if not p: continue
    nm=cstr(u32(p) or 0, 40)
    if not nm: continue
    fl=u32(p+4); ty=u32(p+8); vl=u32(p+0xC)
    rows.append((nm,fl,ty,vl,p))
from collections import defaultdict
byt=defaultdict(list)
for r in rows: byt[r[1]].append(r)
for fl in sorted(byt):
    lst=byt[fl]
    print()
    print('  标志 0x%08X  (%d 个):' % (fl,len(lst)))
    for nm,f,t,v,p in lst[:8]:
        print('     %-32s type=0x%-4X value=0x%08X' % (nm,t,v))
