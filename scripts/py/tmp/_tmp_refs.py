import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def covered(i,n=4): return all(cov[i+k]==1 for k in range(n))
T = 0x0063C5E0
# 1) 作为绝对指针出现
print('=== 1) 绝对指针 0x%08X ===' % T)
pat = struct.pack('<I', T)
i = img.find(pat, 0); n=0
while i>=0:
    if covered(i):
        va=LO+i
        kind='代码' if 0x400000<=va<0x0EA59000 else '数据'
        print('   0x%08X (%s)' % (va,kind))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
# 2) call/jmp rel32
print('=== 2) call/jmp rel32 -> 0x%08X ===' % T)
n=0
for op in (0xE8,0xE9):
    i=img.find(bytes([op]), 0x400000-LO, 0x0EA59000-LO)
    while i>=0:
        if covered(i,5):
            rel=struct.unpack_from('<i',img,i+1)[0]
            if LO+i+5+rel==T:
                print('   0x%08X  %s' % (LO+i, 'call' if op==0xE8 else 'jmp')); n+=1
        i=img.find(bytes([op]), i+1, 0x0EA59000-LO)
print('   共',n)
print()
# 3) 附近还有哪些函数入口, 判断这个函数是否被同族函数引用
print('=== 3) 0x63C5xx 附近的函数入口 ===')
i=img.find(b'\x55\x8b\xec', 0x0063C000-LO, 0x0063D000-LO)
while i>=0:
    if covered(i,3): print('   0x%08X' % (LO+i))
    i=img.find(b'\x55\x8b\xec', i+1, 0x0063D000-LO)
