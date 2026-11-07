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
print('=== 全部 dw_defaultMatchSelect* / dw_default* (剧情选择相关) ===')
# 暴力扫全 dvar 区找名字
found={}
for base in (0x0810F000, 0x0810A000, 0x0810D000, 0x08110000):
    for off in range(0, 0x3000, 4):
        p=base+off
        b=rd(p,16)
        if not b or len(b)<16: continue
        np=struct.unpack_from('<I',b,0)[0]
        nm=cstr(np,60)
        if nm and ('MatchSelect' in nm or 'defaultMatch' in nm or 'PVE' in nm or 'COOP' in nm or 'Coop' in nm):
            found[nm]=p
for nm,p in sorted(found.items()):
    t=u32(p+8); v=u32(p+0xC)
    print('  0x%08X  %-38s type=0x%-4X val=0x%08X (%d)' % (p,nm,t or 0,v or 0,v or 0))
print()
print('=== 找 3291 的同伴 3292 (对比它的用途) ===')
p=0x0810F8A4
b=rd(p,32)
print('  3292 @0x%08X: %s' % (p, b.hex(' ') if b else '?'))
print('     type=0x%X value=0x%X' % (u32(p+8) or 0, u32(p+0xC) or 0))
