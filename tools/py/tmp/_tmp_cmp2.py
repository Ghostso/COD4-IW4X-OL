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
# 对每个 TD, 找到所有 COL, 再由 COL 找到 vtable, 再在堆里搜 vtable 实例
groups = {0x00E6EFDC:'MyEventHandler@dwRoomMatch::Init',
          0x00E6F014:'MyRoomEventHandler@dwPartyImp',
          0x00E6F040:'MyRoomImp@dwPartyImp',
          0x00E6F064:'dwPartyMessageReadyInfo'}
for td,label in groups.items():
    print('='*60)
    print(label)
    pat=struct.pack('<I',td)
    i=img.find(pat,0); cols=[]
    while i>=0:
        va=LO+i
        if 0x00DF0000<=va<0x00E10000: cols.append(va)
        i=img.find(pat,i+1)
    for col in cols:
        cb=rd(col,20)
        if not cb or len(cb)<20: continue
        sig=struct.unpack_from('<I',cb,0)[0]
        if sig!=0: continue
        # COL 被 vtable[-1] 引用; 搜 COL 的引用
        pat2=struct.pack('<I',col)
        j=img.find(pat2,0)
        while j>=0:
            va2=LO+j
            if 0x00DC0000<=va2<0x00DD0000:
                vt=va2+4
                # 数这个 vtable 有多少项
                k=0
                while covok(vt+k*4) and 0x00400000<=struct.unpack('<I',rd(vt+k*4,4))[0]<0x0EA59000:
                    k+=1
                    if k>60: break
                # 搜实例
                patv=struct.pack('<I',vt)
                m=img.find(patv,0); inst=[]
                while m>=0:
                    va3=LO+m
                    if not (vt-0x40<=va3<=vt+0x200) and covok(va3):
                        inst.append(va3)
                    m=img.find(patv,m+1)
                print('  vtable 0x%08X (%d 槽)  实例数=%d %s' % (vt,k,len(inst),[hex(x) for x in inst[:5]]))
            j=img.find(pat2,j+1)
