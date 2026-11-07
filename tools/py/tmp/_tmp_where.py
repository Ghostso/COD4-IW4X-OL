import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
T=0x0063C5E0
pat=struct.pack('<I',T)
print('=== 0x%08X 作为 32 位指针的所有出现 ===' % T)
i=img.find(pat,0)
while i>=0:
    if covok(i):
        va=LO+i
        # 判断所在区域性质
        seg=''
        if 0x00DC7000<=va<0x00DC8000: seg='常量区(可能是 vtable/函数表)'
        elif 0x400000<=va<0x0EA59000: seg='代码段'
        else: seg='数据'
        print('   0x%08X  %s' % (va, seg))
        # 如果像 vtable, 前后各看几项
        if 0x00DC7000<=va<0x00DC8000:
            b=img[(va-0x10)-LO:(va+0x10)-LO]
            print('      前后: %s' % b.hex(' '))
    i=img.find(pat,i+1)
print()
print('=== 0x00DC79C4 附近确认是否真的是一个函数表项 ===')
b=img[(0x00DC7980)-LO:(0x00DC7A00)-LO]
for k in range(0,0x80,4):
    v=struct.unpack_from('<I',b,k)[0]
    tag='<-- 0x63C5E0' if v==T else ''
    print('   0x%08X  %08X  %s' % (0x00DC7980+k, v, tag))
