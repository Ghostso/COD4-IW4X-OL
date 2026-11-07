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
def cstr(va,n=80):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 表区 0x00DC7940 .. 0x00DC7A40 (每 4 字节) ===')
base=0x00DC7940
b=rd(base, 0x100)
if b is None: print('  未覆盖')
else:
    for k in range(0,0x100,4):
        v=struct.unpack_from('<I',b,k)[0]
        tag=''
        if 0x00400000<=v<0x0EA59000: tag='code'
        elif 0x00C00000<=v<0x01000000:
            s=cstr(v,40)
            if s: tag='"%s"'%s
            else: tag='rodata'
        elif v==0: tag='0'
        print('   0x%08X  %08X  %s' % (base+k, v, tag))
