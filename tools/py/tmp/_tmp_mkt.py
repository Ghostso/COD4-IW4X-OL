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
def cstr(va,n=140):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# dwMarketplace 也有 EventHandler - 作对照. 先看它有没有实例
print('=== 对照: dwMarketplace::EventHandler 的 vtable 与实例 ===')
td = 0x00E6E68C-8
pat=struct.pack('<I',td)
i=img.find(pat,0); cols=[]
while i>=0:
    b=rd(LO+i,20)
    if b and len(b)>=20:
        q=struct.unpack('<IIIII',b)
        if q[0]==0 and q[3]==td: cols.append(LO+i)
    i=img.find(pat,i+1)
print('  合法 COL: %s' % [hex(c) for c in cols])
for col in cols:
    b=rd(col,20)
    pCD=struct.unpack_from('<I',b,16)[0]
    print('   COL 0x%08X -> pCD=0x%08X' % (col,pCD))
    # pCD 里含 vtable 偏移? 找 vtable
    i2=img.find(struct.pack('<I',col),0)
    while i2>=0:
        va=LO+i2
        if 0x00DC0000<=va<0x00DD0000:
            vt=va+4
            b2=rd(vt,4)
            print('      vtable @0x%08X 首槽=%s' % (vt,('0x%08X'%struct.unpack('<I',b2)[0]) if b2 else '?'))
            # 实例
            patv=struct.pack('<I',vt)
            m=img.find(patv,0); inst=[]
            while m>=0:
                va3=LO+m
                if not (vt-0x40<=va3<=vt+0x200) and all(cov[va3-LO+k]==1 for k in range(4)):
                    inst.append(va3)
                m=img.find(patv,m+1)
            print('      实例数=%d %s' % (len(inst),[hex(x) for x in inst[:4]]))
        i2=img.find(struct.pack('<I',col),i2+1)
