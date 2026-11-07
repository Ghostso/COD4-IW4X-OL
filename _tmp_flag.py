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
# 0x849B61C 是 "已请求开局" 标志
b=read_va(0x0849B61C,16)
print('=== 0x0849B61C 附近 ===')
print('  ', b.hex(' ') if b else '读不到')
print('  [0x849B61C] =', b[0] if b else '?')
print()
# 0x82E13FC 是被 call [edx+0x3C] 的对象
b2=read_va(0x082E13FC,4)
if b2:
    p=struct.unpack('<I',b2)[0]
    print('  [0x082E13FC] = 0x%08X' % p)
    if p:
        vt=read_va(p,4)
        v=struct.unpack('<I',vt)[0]
        print('    对象 vtable = 0x%08X' % v)
        slot=read_va(v+0x3C,4)
        print('    槽 +0x3C = 0x%08X' % struct.unpack('<I',slot)[0])
