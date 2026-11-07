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
def covok(va,n=4):
    o=va-LO
    return o>=0 and o+n<=len(img) and all(cov[o+k]==1 for k in range(n))
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
for td,label in ((0x00E6EFDC,'MyEventHandler@Init'),(0x00E6F014,'MyRoomEventHandler@Party'),(0x00E6EFA0,'dwRoomMatch')):
    print('='*60)
    print('%s  TD=0x%08X' % (label,td))
    pat=struct.pack('<I',td)
    i=img.find(pat,0)
    while i>=0:
        va=LO+i
        if covok(va):
            cb=rd(va,20)
            if cb and len(cb)>=20:
                q=struct.unpack('<IIIII',cb)
                print('   引用@0x%08X : sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % ((va,)+q))
        i=img.find(pat,i+1)
