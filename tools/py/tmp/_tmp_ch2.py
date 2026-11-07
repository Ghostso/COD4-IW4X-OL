import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
import re
print('=== 宽扫: 含 dvar 的字符串 (大小写不敏感) ===')
seen=set()
for m in re.finditer(rb'[\x20-\x7e]{4,80}', img):
    s=m.group(0)
    if b'dvar' in s.lower() or b'Dvar' in s:
        va=LO+m.start()
        if not (0x400000<=va<0x0EA59000): continue
        if sum(cov[m.start():m.end()])!=len(s): continue
        t=s.decode('latin1')
        if t not in seen:
            seen.add(t)
            print('   0x%08X  %s' % (va,t))
        if len(seen)>60: break
print('   共', len(seen))
