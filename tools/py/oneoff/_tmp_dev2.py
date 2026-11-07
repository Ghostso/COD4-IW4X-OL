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
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== console 相关 dvar (从 dvar 表里找) ===')
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
hits=[]
for g in range(0x0849B700, 0x0849BD00, 4):
    p=u32(g)
    if not p: continue
    nm=cstr(u32(p) or 0, 60)
    if nm and ('con' in nm.lower() or 'dev' in nm.lower() or 'cheat' in nm.lower()):
        hits.append((nm, u32(p+8), u32(p+0xC)))
for nm,t,v in hits:
    print('  %-34s type=0x%-4X value=0x%08X' % (nm, t or 0, v or 0))
print('  共', len(hits))
print()
print('=== "console" 附近的命令行串 ===')
for va in range(0x00DBFFA0, 0x00DC0080, 4):
    s=cstr(va,70)
    if s and len(s)>=3: print('   0x%08X  %s' % (va,s))
