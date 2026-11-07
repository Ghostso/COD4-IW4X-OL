import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def covok(va,n=4):
    o=va-LO
    return o>=0 and o+n<=len(img) and all(cov[o+k]==1 for k in range(n))
def cstr(va,n=140):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 关键: 找 Dvar_SetBool / Dvar_SetInt 之类 API
print('=== 找 dvar 写入 API (在 dvar 注册函数 0x770890 附近) ===')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
for start in (0x770600,0x770700,0x770A00,0x770B00,0x770C00):
    b=rd(start,4)
    if b is None: continue
    print('  0x%08X: %s' % (start, b.hex(' ')))
print()
print('=== 找 "set" 类 dvar 字符串 ===')
for pat in (b'setdvar', b'SetDvar', b'Dvar_Set', b'dvar_set'):
    i=img.find(pat,0)
    if i>=0:
        s=cstr(LO+i,80)
        print('  0x%08X  %s' % (LO+i, s))
    else:
        print('  %-12s 未找到' % pat.decode())
print()
print('=== dvar 3291 句柄被哪些代码读 (已知 20 处) — 有没有写它的 API 调用点 ===')
pat=struct.pack('<I',0x08269818)
i=img.find(pat,0); n=0
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and covok(va):
        print('   0x%08X  前8字节=%s' % (va, img[i-8:i].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
