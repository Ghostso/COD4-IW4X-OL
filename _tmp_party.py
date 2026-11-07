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
def td_of(name_va):
    return name_va-8
print('=== 对照: 解析 dwPartyImp 那组类的 COL/vtable 并查实例 ===')
names = {0x00E6F01C:'MyRoomEventHandler@dwPartyImp', 0x00E6F048:'MyRoomImp@dwPartyImp',
         0x00E6F06C:'dwPartyMessageReadyInfo', 0x00E6EFE4:'MyEventHandler@Init'}
for nva,label in names.items():
    td = nva-8
    pat = struct.pack('<I', td)
    i=img.find(pat,0); cols=[]
    while i>=0:
        va=LO+i
        if 0x00DF0000<=va<0x00E10000: cols.append(va)
        i=img.find(pat,i+1)
    print()
    print('  %s' % label)
    print('    TD=0x%08X  COL引用: %s' % (td,[hex(c) for c in cols] or '无'))
    for col in cols[:3]:
        cb=rd(col,20)
        if not cb or len(cb)<20: continue
        sig,off,cd,pTD,pCD = struct.unpack('<IIIII',cb)
        if sig!=0: continue
        # COL 通常被 vtable[-1] 引用; 找它之后 +8 的 vtable
        pat2=struct.pack('<I',col)
        j=img.find(pat2,0)
        while j>=0:
            va2=LO+j
            if 0x00DC0000<=va2<0x00DD0000:
                vt=va2+4
                b2=rd(vt,4)
                print('      COL 0x%08X -> vtable 0x%08X 首槽=%s' % (col,vt, ('0x%08X'%struct.unpack('<I',b2)[0]) if b2 else '?'))
            j=img.find(pat2,j+1)
