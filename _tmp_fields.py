import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=110):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
SING = 0x3B2BBE80
print('=== 单例对象的几个关键字段 (live snap_002) ===')
for off in (0x105F0,0x105FC,0x10600,0x10604,0x10608,0x1060C,0x10610,0x10614,0x10618,0x1061C,0x10750):
    b=rd(SING+off,4)
    if not b: print('  +0x%-6X 未覆盖' % off); continue
    v=struct.unpack('<I',b)[0]
    s=cstr(SING+off, 32) if off in (0x105F0,0x10750) else None
    print('  +0x%-6X = 0x%08X (%d)%s' % (off, v, v, ('  "%s"'%s) if s else ''))
print()
print('=== 字符串 0xdb7c10 (playlist) 附近 ===')
for va in range(0x00DB7BD0, 0x00DB7C80, 4):
    s=cstr(va,40)
    if s and len(s)>=3: print('  0x%08X  %s' % (va,s))
