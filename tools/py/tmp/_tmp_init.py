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
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== RTTI 名区 0x00E6EF80..0x00E6F040 (dwRoomMatch 相关) ===')
for va in range(0x00E6EF80, 0x00E6F040, 4):
    s=cstr(va,110)
    if s and ('.?A' in s or 'dwRoom' in s):
        print('   0x%08X  %s' % (va,s))
print()
print('=== 0x00DC78F0 vtable 的 COL 结构 ===')
# vtable[-1] @ 0x00DC78EC = COL
b=rd(0x00DC78EC,4)
col=struct.unpack('<I',b)[0]
print('  COL = 0x%08X' % col)
cb=rd(col,20)
print('  内容:', cb.hex(' ') if cb else '?')
if cb:
    sig,off,cd,pTD,pCD = struct.unpack('<IIIII', cb)
    print('  sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % (sig,off,cd,pTD,pCD))
    nm=rd(pTD+8,110)
    if nm:
        e=nm.find(b'\x00')
        print('  RTTI = %s' % nm[:e].decode('latin1'))
    print('  pCD(TypeDescriptor of class) = 0x%08X' % pCD)
    nm2=rd(pCD+8,110)
    if nm2:
        e=nm2.find(b'\x00')
        print('  类名 = %s' % nm2[:e].decode('latin1'))
