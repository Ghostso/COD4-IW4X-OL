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
def cstr(va,n=96):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 1) 名字 "3291" 在 0x00DE6954，找它的注册点(代码里 push 0xde6954)
print('=== 1) push 0x00DE6954 (注册点) ===')
pat = struct.pack('<I', 0x00DE6954)
i = img.find(pat, 0)
n=0
while i>=0 and n<10:
    if cov[i]==1:
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            print('   0x%08X  %s' % (va, img[max(0,i-6):i+14].hex(' ')))
            n+=1
    i=img.find(pat,i+1)
print('  共',n)
print()
# 2) 全局槽 0x08269818 的引用
print('=== 2) 引用全局槽 0x08269818 的代码 ===')
pat2 = struct.pack('<I', 0x08269818)
i = img.find(pat2, 0)
n=0
while i>=0 and n<15:
    if cov[i]==1:
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            print('   0x%08X  %s' % (va, img[max(0,i-8):i+14].hex(' ')))
            n+=1
    i=img.find(pat2,i+1)
print('  共',n)
print()
# 3) dvar 对象 0x0810F7C0 自身的指针引用
print('=== 3) 引用 dvar 对象 0x0810F7C0 ===')
pat3 = struct.pack('<I', 0x0810F7C0)
i = img.find(pat3, 0)
n=0
while i>=0 and n<15:
    if cov[i]==1:
        va=LO+i
        print('   0x%08X (%s)' % (va, '代码' if 0x400000<=va<0x0EA59000 else '数据'))
        n+=1
    i=img.find(pat3,i+1)
print('  共',n)
