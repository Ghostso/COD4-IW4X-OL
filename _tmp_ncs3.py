import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
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
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 引用 ncs_network_dvar (0x00DC9C18) 的代码 ===')
pat=struct.pack('<I',0x00DC9C18)
i=img.find(pat,0); n=0
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and all(cov[i+k]==1 for k in range(4)):
        print('   0x%08X  前12字节=%s' % (va, img[i-12:i].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 引用 ncs_codinfo_dvar (0x00DC9BEC) ===')
pat=struct.pack('<I',0x00DC9BEC)
i=img.find(pat,0); n=0
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and all(cov[i+k]==1 for k in range(4)):
        print('   0x%08X  前12字节=%s' % (va, img[i-12:i].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 关键: ncs_%s_%s (0x00DC99D4) 的模板用法 ===')
pat=struct.pack('<I',0x00DC99D4)
i=img.find(pat,0); n=0
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and all(cov[i+k]==1 for k in range(4)):
        print('   0x%08X  前12字节=%s' % (va, img[i-12:i].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
