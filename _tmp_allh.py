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
print('=== 整个函数里所有 dvar 注册的结果句柄 (证明都执行了) ===')
slots = [
 (0x08269824,'1751'),(0x08269840,'1752'),(0x08269784,'1753'),(0x0826984C,'1754'),
 (0x0826981C,'1755'),(0x08269834,'1756'),(0x0826982C,'3291'),
 (0x08269818,'1758'),(0x08269788,'xblive_privatematch'),(0x08269848,'?'),
 (0x08269828,'3292/splitscreen'),(0x08269858,'1760'),(0x08269850,'1761'),
 (0x08269838,'1762'),(0x08269820,'1764'),(0x0826985C,'1765'),(0x08269830,'末次返回'),
 (0x0826978C,'?esi'),(0x082E1394,'?'),(0x082E1398,'?'),
]
def cstr(va,n=64):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
ok=0; bad=0
for g,label in slots:
    b=rd(g,4)
    if not b:
        print('  [0x%08X] 未覆盖' % g); continue
    p=struct.unpack('<I',b)[0]
    nm=None
    if p:
        ob=rd(p,8)
        if ob: nm=cstr(struct.unpack('<I',ob)[0])
    status = 'OK' if p else 'NULL'
    if p: ok+=1
    else: bad+=1
    print('  [0x%08X] -> 0x%08X  %-8s  实测名=%s (写于 %s)' % (g,p,status,('\"%s\"'%nm) if nm else '?',label))
print()
print('  非空 %d 个 / 空 %d 个' % (ok,bad))
