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
print('=== setdvar 字符串 0x00DC0DBC 附近还有哪些命令 ===')
for va in range(0x00DC0D80, 0x00DC0E40, 4):
    s=cstr(va,60)
    if s and len(s)>=3: print('   0x%08X  %s' % (va,s))
print()
print('=== 谁引用 setdvar 字符串 (注册点) ===')
pat=struct.pack('<I',0x00DC0DBC)
i=img.find(pat,0); n=0
while i>=0:
    if covok(LO+i):
        print('   0x%08X' % (LO+i)); n+=1
    i=img.find(pat,i+1)
print('   共',n)
