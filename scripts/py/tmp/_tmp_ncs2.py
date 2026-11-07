import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\FIXMC_20261027_140146'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=130):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== NCS 相关串全部 (含 network_dvar / codinfo) ===')
for va in range(0x00DC9B80, 0x00DC9D00, 4):
    s=cstr(va,120)
    if s and len(s)>=5: print('   0x%08X  %s' % (va,s))
print()
print('=== 引用 mp/scriptClientData.csv (0x00DC9A64) 的代码 ===')
pat=struct.pack('<I',0x00DC9A64)
i=img.find(pat,0); n=0
while i>=0:
    va=LO+i
    if 0x400000<=va<0x0EA59000 and all(cov[i+k]==1 for k in range(4)):
        print('   0x%08X  前8字节=%s' % (va, img[i-8:i].hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
