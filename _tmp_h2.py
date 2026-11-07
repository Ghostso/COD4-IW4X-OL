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
def cstr(va,n=96):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
def show(va,label=''):
    b=rd(va,4)
    if not b: return
    p=struct.unpack('<I',b)[0]
    ob=rd(p,20)
    if not ob: return
    w=struct.unpack('<5I',ob)
    nm=cstr(w[0])
    print('  [0x%08X]%s -> 0x%08X  name=%-14s type=0x%X val=%d' %
          (va, label, p, ('"%s"'%nm) if nm else '?', w[2], w[3]))
print('=== 0x008088xx 那段注册出来的句柄槽 ===')
for va in (0x0826982C, 0x08269818, 0x08269788):
    show(va)
print()
print('=== 名字池里 0xDE68xx..0xDE69xx 的串 ===')
for base in range(0x00DE6880, 0x00DE69C0, 4):
    s=cstr(base, 40)
    if s and len(s)>=2:
        print('  0x%08X  %s' % (base, s))
