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
G = 0x08269818
b = rd(G,4)
print('=== [0x%08X] ===' % G)
if not b:
    print('  不可达/未覆盖')
else:
    p = struct.unpack('<I', b)[0]
    print('  -> 0x%08X' % p)
    if p:
        ob = rd(p, 24)
        if ob:
            w = struct.unpack('<6I', ob)
            nm = cstr(w[0])
            print('  dvar_t: name=0x%08X %s' % (w[0], ('"%s"'%nm) if nm else ''))
            print('          +0x04=0x%08X  +0x08=type 0x%X  +0x0C=值 0x%08X (%d)'
                  % (w[1], w[2], w[3], w[3]))
            fv = struct.unpack('<f', struct.pack('<I', w[3]))[0]
            print('          float 解释 = %.4f' % fv)
        else:
            print('  对象内存未覆盖')
print()
print('=== 顺带看这个全局槽附近还有哪些 dvar 槽被用到 ===')
for g in range(0x08269800, 0x08269840, 4):
    bb = rd(g,4)
    if not bb: continue
    p = struct.unpack('<I', bb)[0]
    if not (0x08000000 <= p < 0x09000000): continue
    ob = rd(p,12)
    if not ob: continue
    nm = cstr(struct.unpack('<I', ob)[0])
    if nm and len(nm)>=3:
        typ, val = struct.unpack_from('<II', ob, 8)
        print('  [0x%08X] -> 0x%08X  %-30s type=0x%X val=0x%08X' % (g,p,nm,typ,val))
