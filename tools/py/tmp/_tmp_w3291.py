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
# dvar "3291" 对象在 0x0810F7C0。找所有引用它的代码点
print('=== 引用 dvar 对象 0x0810F7C0 的位置 ===')
pat=struct.pack('<I',0x0810F7C0)
i=img.find(pat,0); n=0
while i>=0 and n<20:
    if cov[i]==1:
        va=LO+i
        kind='代码' if 0x400000<=va<0x0EA59000 else '数据'
        print('   0x%08X (%s)  %s' % (va, kind, img[max(0,i-10):i+14].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('  共',n)
print()
print('=== 引用全局槽 0x08269818 的写指令候选 (排除已知读点) ===')
pat2=struct.pack('<I',0x08269818)
i=img.find(pat2,0); n=0
while i>=0 and n<25:
    if cov[i]==1:
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            pre=img[max(0,i-4):i]
            print('   0x%08X  前4字节=%s' % (va, pre.hex(' ')))
            n+=1
    i=img.find(pat2,i+1)
