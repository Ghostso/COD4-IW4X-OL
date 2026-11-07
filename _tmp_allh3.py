import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img): return None
    if sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=64):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
slots = [
 (0x08269824,'1751'),(0x08269840,'1752'),(0x08269784,'1753'),(0x0826984C,'1754'),
 (0x0826981C,'1755'),(0x08269834,'1756'),(0x0826982C,'1755的返回?'),
 (0x08269818,'3291'),(0x08269788,'1758/xblive'),
 (0x08269828,'splitscreen'),(0x08269858,'1760'),(0x08269850,'1761'),
 (0x08269838,'1762'),(0x08269820,'1764'),(0x0826985C,'1765'),(0x08269830,'末次返回'),
]
ok=0; null=0
for g,label in slots:
    b=rd(g,4)
    if b is None or len(b)<4:
        print('  [0x%08X] 未覆盖      (期望 %s)' % (g,label)); continue
    p=struct.unpack('<I',b)[0]
    nm=None
    if p:
        ob=rd(p,4)
        if ob is not None and len(ob)==4:
            nm=cstr(struct.unpack('<I',ob)[0])
    if p: ok+=1
    else: null+=1
    print('  [0x%08X] -> 0x%08X %-4s  实测名=%-16s (期望 %s)' % (g,p,'OK' if p else 'NULL',('\"%s\"'%nm) if nm else '?',label))
print()
print('  非空 %d / 空 %d' % (ok,null))
