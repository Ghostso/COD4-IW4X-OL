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
            return f[o:o+n]
    return None
def cstr(va, n=64):
    b = read_va(va, n)
    if not b: return None
    e = b.find(b'\x00')
    return b[:e].decode('latin1') if e>=0 else b.decode('latin1')
# 从 0x0810AD60 起，按 16 字节一格解 dvar_t(name_ptr, type, pad, value)
print('=== 0x0810AD60 .. 0x0810AF20 ===')
va = 0x0810AD60
blk = read_va(va, 0x1C0)
for k in range(0, 0x1C0, 16):
    name_p, typ = struct.unpack_from('<II', blk, k)
    val, pad = struct.unpack_from('<II', blk, k+8)
    nm = cstr(name_p)
    ok = nm is not None and all(32<=ord(c)<127 for c in nm) and len(nm)>=2
    print('  0x%08X  name=0x%08X %-32s type=%-3d value=0x%08X(%d)' %
          (va+k, name_p, ('"%s"'%nm) if ok else '?', typ, val, val))
