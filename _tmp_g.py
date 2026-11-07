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
for va in (0x082E13FC, 0x082E1514, 0x082E1520, 0x082E1524, 0x082E1558, 0x0849B61C, 0x0849B7A4):
    b=read_va(va,4)
    if b: print('  [0x%08X] = 0x%08X' % (va, struct.unpack('<I',b)[0]))
    else: print('  [0x%08X] 不可达' % va)
