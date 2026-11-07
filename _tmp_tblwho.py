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
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
# 表里引用 0x63C5E0 的位置是 0x00DC79C4，往前找表头(第一项)
# 先看这张表被谁用: 搜指向表内地址的指针
print('=== 搜指向表区间 0x00DC7940..0x00DC7A40 的指针 ===')
lo,hi=0x00DC7940,0x00DC7A40
found=[]
import struct as st
for va in range(lo,hi,4):
    pat=st.pack('<I',va)
    i=img.find(pat,0)
    while i>=0:
        if covok(i):
            v=LO+i
            if not (lo<=v<hi):
                found.append((v,va))
        i=img.find(pat,i+1)
seen=set()
for v,tgt in found:
    key=(v//4)*4
    s=cstr=None
    kind='代码' if 0x400000<=v<0x0EA59000 else ('数据' if v>=0x0DC0000 or v<0x00400000 else '其他')
    print('   0x%08X -> 表+0x%X' % (v, tgt-lo))
print()
# 更直接: 搜整个表首地址
for tb in (0x00DC7940,0x00DC7958,0x00DC7900,0x00DC7980):
    pat=st.pack('<I',tb)
    i=img.find(pat,0); n=0
    while i>=0 and n<6:
        if covok(i): print('   引用表 0x%08X 的位置: 0x%08X' % (tb, LO+i)); n+=1
        i=img.find(pat,i+1)
