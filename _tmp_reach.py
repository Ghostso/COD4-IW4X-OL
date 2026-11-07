import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def find_region(va):
    for base,size,fn in idxs:
        if base <= va < base+size: return base,size,fn
    return None
def read_va(va,n):
    r=find_region(va)
    if not r: return None
    base,size,fn=r
    f=open(os.path.join(D,fn),'rb').read()
    return f[va-base:va-base+n]
obj=0x3D5BB008
print('对象基址 0x%08X' % obj)
for off in (0x283,0x105FC,0x10614,0x106F8,0x38710,0x10768,0x10770,0x10758,0x1075C):
    va=obj+off
    r=find_region(va)
    if not r:
        print('  +0x%-7X 0x%08X  *** 不可达(对象没有这么长) ***' % (off,va)); continue
    base,size,fn=r
    b=read_va(va,1)
    print('  +0x%-7X 0x%08X  region base=0x%08X size=0x%X  byte=%s' % (off,va,base,size,b.hex() if b else '?'))
print()
print('=== 对象实际占用多少连续区域 ===')
base,size,fn = find_region(obj)
print('  对象所在 region: base=0x%08X size=0x%X (%d KB) file=%s' % (base,size,size//1024,fn))
print('  对象到 region 末尾还剩 0x%X 字节' % (base+size-obj))
