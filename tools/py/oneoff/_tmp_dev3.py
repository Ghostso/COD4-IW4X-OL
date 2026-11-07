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
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 按 0xDC0Dxx 那片脚本内置函数表往前看, 还有什么命令 ===')
base=0x00DAA400
b=rd(base,0x200)
for k in range(0,0x200,8):
    np=struct.unpack_from('<I',b,k)[0]
    fp=struct.unpack_from('<I',b,k+4)[0]
    if not (0x00C00000<=np<=0x01100000): continue
    nm=cstr(np,50)
    if nm and 0x400000<=fp<0x0EA59000:
        print('   0x%08X  %-30s fn=0x%08X' % (base+k, nm, fp))
