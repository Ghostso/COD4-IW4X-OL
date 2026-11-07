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
for g,label in ((0x0826982C,'dvar 3291 句柄槽'),(0x08269818,'★ dvar 1758 句柄槽'),(0x08269788,'xblive_privatematch')):
    b=rd(g,4)
    if not b: print('%s [0x%08X] 不可达' % (label,g)); continue
    p=struct.unpack('<I',b)[0]
    ob=rd(p,20) if p else None
    if not ob: print('%s [0x%08X] -> 0x%08X (对象不可达)' % (label,g,p)); continue
    w=struct.unpack('<5I',ob)
    nm=cstr(w[0])
    print('%s [0x%08X] -> 0x%08X  name=%s  type=0x%X  值=%d (0x%X)'
          % (label,g,p,('"%s"'%nm) if nm else '?', w[2], w[3], w[3]))
