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
def u32(va):
    b=rd(va,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
groups = {0x00E6EFDC:'MyEventHandler@dwRoomMatch::Init',
          0x00E6F014:'MyRoomEventHandler@dwPartyImp',
          0x00E6F040:'MyRoomImp@dwPartyImp',
          0x00E6F064:'dwPartyMessageReadyInfo',
          0x00E6EFA0:'dwRoomMatch'}
for td,label in groups.items():
    print('='*62)
    print('%-36s TD=0x%08X' % (label,td))
    pat=struct.pack('<I',td)
    i=img.find(pat,0); cols=[]
    while i>=0:
        va=LO+i
        if covok(va): cols.append(va)
        i=img.find(pat,i+1)
    for col in cols:
        cb=rd(col,20)
        if not cb or len(cb)<20: continue
        sig,off,cd,pTD,pCD = struct.unpack('<IIIII',cb)
        if sig!=0 or pTD!=td: continue
        pat2=struct.pack('<I',col)
        j=img.find(pat2,0)
        while j>=0:
            va2=LO+j
            if 0x00DC0000<=va2<0x00DD0000:
                vt=va2+4
                k=0
                while True:
                    v=u32(vt+k*4)
                    if v is None or not (0x00400000<=v<0x0EA59000): break
                    k+=1
                    if k>80: break
                patv=struct.pack('<I',vt)
                m=img.find(patv,0); inst=[]
                while m>=0:
                    va3=LO+m
                    if not (vt-0x40<=va3<=vt+0x200) and covok(va3): inst.append(va3)
                    m=img.find(patv,m+1)
                print('   COL 0x%08X -> vtable 0x%08X (%d 槽), 实例=%d %s'
                      % (col,vt,k,len(inst),[hex(x) for x in inst[:4]]))
            j=img.find(pat2,j+1)
