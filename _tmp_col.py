import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
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
VT=0x00DC78F0
print('=== 0x00DC78E0..0x00DC78F4 ===')
b=rd(0x00DC78E0,0x18)
for k in range(0,0x18,4):
    v=struct.unpack_from('<I',b,k)[0]
    print('   0x%08X  %08X' % (0x00DC78E0+k, v))
print()
print('=== 尝试 -8 处的 COL ===')
for back in (8,):
    b=rd(VT-back,4)
    if not b: continue
    col=struct.unpack('<I',b)[0]
    print('  vtable[-%d] = 0x%08X' % (back,col))
    cb=rd(col,20)
    if cb:
        try:
            sig,off,cd,pTD,pCD = struct.unpack('<IIIII', cb)
            print('    sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % (sig,off,cd,pTD,pCD))
            nm=cstr(pTD+8,110); nm2=cstr(pCD+8,110)
            print('    RTTI(子) = %s' % nm)
            print('    类名 = %s' % nm2)
        except Exception as e: print('   ', e)
print()
print('=== 直接看 0x00DF869C (上次推出的 COL) ===')
cb=rd(0x00DF869C,20)
if cb:
    sig,off,cd,pTD,pCD = struct.unpack('<IIIII', cb)
    print('   sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % (sig,off,cd,pTD,pCD))
    print('   RTTI =', cstr(pTD+8,110))
    print('   类名 =', cstr(pCD+8,110))
