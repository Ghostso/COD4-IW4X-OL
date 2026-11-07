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
# 1) 找所有 call 0x770890 (bool dvar 注册) 与 0x770940 (int dvar 注册)
print('=== 所有 call 到 0x770890 / 0x770940 的位置 (限 0x800000..0x810000) ===')
for lo,hi in ((0x00800000,0x00820000),):
    n890=n940=0
    lst=[]
    i=img.find(b'\xE8', lo-LO, hi-LO)
    while i>=0:
        if cov[i]==1:
            rel=struct.unpack_from('<i',img,i+1)[0]
            t=LO+i+5+rel
            if t in (0x770890,0x770940):
                lst.append((LO+i, hex(t)))
        i=img.find(b'\xE8', i+1, hi-LO)
    print('  共 %d 处' % len(lst))
    for a,t in lst[:8]: print('   0x%08X -> %s' % (a,t))
    if len(lst)>8: print('   ... 首尾: 0x%08X .. 0x%08X' % (lst[0][0], lst[-1][0]))
print()
# 2) 从 0x808830 往前找函数序言
print('=== 0x808400..0x808900 里所有 55 8B EC (函数序言) ===')
seg_lo=0x00808400; seg_hi=0x00808A00
o0=seg_lo-LO
found=[]
i=img.find(b'\x55\x8b\xec', o0, seg_hi-LO)
while i>=0:
    if cov[i]==1 and cov[i+1]==1 and cov[i+2]==1:
        found.append(LO+i)
    i=img.find(b'\x55\x8b\xec', i+1, seg_hi-LO)
for a in found: print('   0x%08X' % a)
print('  共', len(found))
