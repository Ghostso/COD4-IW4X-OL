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
def cstr(va,n=160):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# dvar "3291" 对象
h=u32(0x08269818)
print('=== dvar 3291 对象 ===')
print('  句柄 0x%08X' % (h or 0))
if h:
    name_ptr=u32(h)
    print('  name_ptr = 0x%08X -> %r' % (name_ptr or 0, cstr(name_ptr or 0, 80)))
    print('  +0x04 = 0x%08X' % (u32(h+4) or 0))
    print('  +0x08 type=0x%X' % (u32(h+8) or 0))
    print('  +0x0C value=0x%08X (%d)' % (u32(h+0xC) or 0, u32(h+0xC) or 0))
print()
print('=== 周围同族 dvar 的名字 (看清这一组是干什么的) ===')
for g in (0x0826981C,0x08269820,0x08269824,0x08269828,0x0826982C,0x08269830,0x08269818,0x08269834,0x08269838):
    o=u32(g)
    if not o: print('  [0x%08X] = 0' % g); continue
    nm=cstr(u32(o) or 0, 60)
    print('  [0x%08X] -> 0x%08X  name=%s  val=0x%08X' % (g,o,nm,u32(o+0xC) or 0))
