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
            return f[va-base:va-base+n], fn
    return None, None
obj=0x3D5BB008
b,fn = read_va(obj, 0x30)
print('=== 对象 0x%08X 头部 0x30 字节 (%s) ===' % (obj, fn))
for k in range(0,0x30,16):
    print('  +0x%02X  %s' % (k, b[k:k+16].hex(' ')))
print()
vt=struct.unpack('<I', b)[0]
print('vtable = 0x%08X' % vt)
# 这个 vtable 有多少槽？找它后面的第一个非代码指针
for k in range(0, 0x180, 4):
    v=struct.unpack('<I', read_va(vt+k,4)[0])[0]
    tag = 'code' if (0x400000 <= v < 0x0EA59000) else '---'
    if k%16==0 or tag=='---':
        print('   +0x%03X  0x%08X %s' % (k, v, tag))
    if tag=='---' and k>0x40: break
