import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
for T,name in ((0x0063A720,'type0'),(0x0063A770,'type1'),(0x0063A7C0,'type2')):
    print('=== %s  0x%08X 作为 32 位指针 ===' % (name,T))
    pat=struct.pack('<I',T)
    i=img.find(pat,0); n=0
    while i>=0:
        if covok(i):
            va=LO+i
            seg=''
            if 0x400000<=va<0x0EA59000: seg='代码段(立即数)'
            elif 0x00DC0000<=va<0x00DD0000: seg='常量/vtable区'
            else: seg='数据'
            print('   0x%08X  %s' % (va,seg))
            n+=1
        i=img.find(pat,i+1)
    if n==0: print('   无')
    print()
