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
print('=== 表区 0x00DC78D0..0x00DC7930 ===')
base=0x00DC78D0
b=rd(base,0x60)
if b:
    for k in range(0,0x60,4):
        v=struct.unpack_from('<I',b,k)[0]
        tag=''
        if 0x400000<=v<0x0EA59000: tag='code'
        elif 0x00C00000<=v<0x01100000: tag='rodata'
        print('   0x%08X  %08X  %s' % (base+k, v, tag))
print()
print('=== 该 vtable 的 RTTI (vtable[-1]) ===')
for VT in (0x00DC78F0,):
    for back in (4,8,12):
        b=rd(VT-back,4)
        if b:
            v=struct.unpack('<I',b)[0]
            if 0x00C00000<=v<0x01100000:
                cb=rd(v,20)
                if cb:
                    pTD=struct.unpack_from('<I',cb,12)[0]
                    nm=rd(pTD+8,80)
                    if nm and nm[:1]==b'.':
                        e=nm.find(b'\x00')
                        print('  vtable 0x%08X  (VT-%d) COL=0x%08X -> %s' % (VT,back,v,nm[:e].decode('latin1')))
