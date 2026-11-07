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
def cstr(va,n=140):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== RTTI 名区 0x00E6E000..0x00E72000 里所有 dw* 类 ===')
lo=0x00E6E000; hi=0x00E72000
for va in range(lo,hi,4):
    s=cstr(va,140)
    if s and s.startswith('.?AV') and ('dw' in s or 'Room' in s or 'Party' in s or 'Match' in s):
        print('   0x%08X  %s' % (va,s))
