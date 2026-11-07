import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def read_va(va,n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n]
    return None
def cstr(va,n=64):
    b=read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 收集所有 dvar 对象，按 type 归类，看每类的值像什么
rows=[]
for g in range(0x0849B700, 0x0849BC00, 4):
    b=read_va(g,4)
    if not b: continue
    p=struct.unpack('<I',b)[0]
    if not (0x08100000 <= p <= 0x08120000): continue
    ob=read_va(p,32)
    if not ob: continue
    w=struct.unpack_from('<8I',ob,0)
    nm=cstr(w[0])
    if not nm or len(nm)<3: continue
    rows.append((nm,w,g,p))
from collections import defaultdict
byt=defaultdict(list)
for nm,w,g,p in rows: byt[w[2]].append((nm,w,g,p))
for t in sorted(byt):
    lst=byt[t]
    print('=== type=0x%X  (共 %d 个) ===' % (t, len(lst)))
    for nm,w,g,p in lst[:6]:
        s=''
        if nm and len(nm)>=3 and all(32<=ord(c)<127 for c in nm):
            sv=cstr(w[3]) if 0x00400000<=w[3]<=0x10000000 else None
            if sv: s='  -> 串 %r' % sv
        print('   %-34s @3=0x%08X(%d)%s' % (nm, w[3], w[3], s))
    print()
