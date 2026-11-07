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
def cstr(va,n=100):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 两个 vtable 的 RTTI 名
print('=== 找两个 vtable 的 RTTI ===')
for VT in (0x00DC795C, 0x00DC7274):
    print()
    print('vtable 0x%08X:' % VT)
    # MSVC vtable[-1] = CompleteObjectLocator
    b=rd(VT-4,4)
    if b:
        col=struct.unpack('<I',b)[0]
        print('  vtable[-1] (COL) = 0x%08X' % col)
        if col:
            cb=rd(col,20)
            if cb:
                print('  COL: %s' % cb.hex(' '))
                pTD=struct.unpack_from('<I',cb,12)[0]
                print('  pTypeDescriptor = 0x%08X' % pTD)
                nb=rd(pTD,4)
                if nb:
                    td=read_va=None
                    # TypeDescriptor: +0 pVFTable, +4 spare, +8 name
                    nm=rd(pTD+8,80)
                    if nm:
                        e=nm.find(b'\x00')
                        s=nm[:e].decode('latin1') if e>0 else nm.decode('latin1')
                        print('  RTTI 名 = %s' % s)
    # 也试 VT-8 等其他位置
    for d0 in (8,12,16):
        b=rd(VT-d0,4)
        if b:
            v=struct.unpack('<I',b)[0]
            if 0x00C00000<=v<0x01100000:
                cb=rd(v,20)
                if cb:
                    pTD=struct.unpack_from('<I',cb,12)[0]
                    nm=rd(pTD+8,80)
                    if nm and nm[:1] in (b'.',):
                        e=nm.find(b'\x00')
                        print('  (VT-%d) COL=0x%08X -> RTTI %s' % (d0,v,nm[:e].decode('latin1')))
