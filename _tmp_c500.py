import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def covok(i,n=4): return all(cov[i+k]==1 for k in range(n))
T=0x0063B500
print('=== 1) call/jmp rel32 -> 0x%08X ===' % T)
n=0
for op in (0xE8,0xE9):
    i=img.find(bytes([op]), 0x400000-LO, 0x0EA59000-LO)
    while i>=0:
        if covok(i,5):
            rel=struct.unpack_from('<i',img,i+1)[0]
            if LO+i+5+rel==T:
                print('   0x%08X  %s' % (LO+i,'call' if op==0xE8 else 'jmp')); n+=1
        i=img.find(bytes([op]),i+1,0x0EA59000-LO)
print('   共',n)
print()
print('=== 2) 绝对指针 0x%08X ===' % T)
pat=struct.pack('<I',T)
i=img.find(pat,0); n=0
while i>=0:
    if covok(i):
        va=LO+i
        seg='vtable/常量区' if 0x00DC0000<=va<0x00DD0000 else ('代码' if 0x400000<=va<0x0EA59000 else '数据')
        print('   0x%08X  %s' % (va,seg)); n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 3) 0x63B56D "combat" 分支 / [edi+0x24] 的含义 ===')
print('   edi = [dwRoomImp 单例]->vtable+0x74 的返回值')
print('   [edi+0x24] 是那个对象的一个字节标志')
