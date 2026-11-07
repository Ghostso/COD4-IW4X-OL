import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
def read_va(va, n):
    for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
        if line.startswith('#'): continue
        p = line.split()
        if len(p) < 5: continue
        base, size = int(p[0],16), int(p[1],16)
        if base <= va < base+size:
            f = open(os.path.join(D,p[4]),'rb').read()
            o = va-base
            return f[o:o+n], p[4]
    return None, None
def cstr(va, n=48):
    b,_ = read_va(va, n)
    if not b: return None
    e = b.find(b'\x00')
    return b[:e].decode('latin1') if e>=0 else None
va=0x0810A800
blk, fn = read_va(va, 0x100)
print('=== 0x0810A87C 附近 (区域 %s) ===' % fn)
for k in range(0, 0x100, 16):
    q = struct.unpack_from('<IIII', blk, k)
    print('  0x%08X  %08X %08X %08X %08X' % (va+k, *q))
print()
print('=== 0x0810AD88 起 0x120 原始分析 ===')
blk2, fn2 = read_va(0x0810AD88, 0x120)
for k in range(0, 0x120, 16):
    q = struct.unpack_from('<IIII', blk2, k)
    a = cstr(q[0])
    tag = ('"%s"' % a) if a and len(a)>=2 else ''
    print('  0x%08X  %08X %08X %08X %08X  %s' % (0x0810AD88+k, *q, tag))
