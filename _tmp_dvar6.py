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
    s=b[:e]
    try: t=s.decode('ascii')
    except: return None
    if all(32<=ord(c)<127 for c in t): return t
    return None
print('=== 扫描 0x0849B700..0x0849B900 的 dvar 句柄 ===')
rows=[]
for g in range(0x0849B700, 0x0849B900, 4):
    b=read_va(g,4)
    if not b: continue
    p=struct.unpack('<I',b)[0]
    if not (0x08100000 <= p <= 0x08120000): continue
    ob=read_va(p,24)
    if not ob: continue
    w=struct.unpack_from('<6I',ob,0)
    nm=cstr(w[0])
    if not nm or len(nm)<3: continue
    rows.append((g,p,nm,w))
for g,p,nm,w in rows:
    fv=struct.unpack('<f', struct.pack('<I',w[3]))[0]
    print('  [0x%08X] %-32s -> 0x%08X  @1=0x%X @2=0x%X @3=0x%08X(%d / %.3f)' % (g,nm,p,w[1],w[2],w[3],w[3],fv))
print()
print('dw_ 开头的:')
for g,p,nm,w in rows:
    if nm.startswith('dw_'):
        fv=struct.unpack('<f', struct.pack('<I',w[3]))[0]
        print('  %-34s 值=%d (float %.3f)' % (nm, w[3], fv))
