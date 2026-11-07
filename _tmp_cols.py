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
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 两个 COL 指向的类 ===')
for col in (0x00DF7764, 0x00DF8648):
    b=rd(col,20)
    if not b: print('  0x%08X 未覆盖'%col); continue
    sig,off,cd,pTD,pCD = struct.unpack('<IIIII', b)
    print('  COL 0x%08X: sig=%d off=%d cd=%d' % (col,sig,off,cd))
    print('     pTD=0x%08X -> %s' % (pTD, cstr(pTD+8,110)))
    print('     pCD=0x%08X' % pCD)
print()
print('=== 各 COL 被哪些 vtable 引用 ===')
for col in (0x00DF7764,0x00DF8648,0x00DF869C):
    pat=struct.pack('<I',col)
    i=img.find(pat,0); n=0
    while i>=0 and n<6:
        va=LO+i
        if 0x00DC0000<=va<0x00DD0000:
            vt_guess=va+8
            print('  COL 0x%08X  在 0x%08X -> vtable 可能 = 0x%08X, 首项=?' % (col,va,vt_guess))
            b=rd(vt_guess,4)
            if b: print('        首槽 = 0x%08X' % struct.unpack('<I',b)[0])
            n+=1
        i=img.find(pat,i+1)
