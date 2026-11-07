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
def cstr(va,n=100):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
VT=0x00DC7274
print('=== 找 vtable 0x%08X 的 RTTI (前面的 CompleteObjectLocator) ===' % VT)
pat=struct.pack('<I',VT)
i=img.find(pat,0)
while i>=0:
    if all(cov[i+k]==1 for k in range(4)):
        va=LO+i
        if va<VT:
            col=va-4
            print('  指针在 0x%08X  (COL 候选 0x%08X)' % (va,col))
            b=rd(col-12,20)
            if b: print('     COL-12 起: ', b.hex(' '))
    i=img.find(pat,i+1)
print()
print('=== 该 vtable 是否紧跟在 RTTI 结构后 (看 0x00DC7260 附近) ===')
b=rd(0x00DC7250,0x40)
if b:
    for k in range(0,0x40,4):
        v=struct.unpack_from('<I',b,k)[0]
        s=cstr(v,60) if 0x00C00000<=v<0x01100000 else None
        print('   0x%08X  %08X  %s' % (0x00DC7250+k, v, ('\"%s\"'%s[:60]) if s else ''))
print()
print('=== 搜 RTTI 名 .?AV... 在 0x00E6F000..0x00E80000 附近, 与这个类相关 ===')
# 直接找所有含 Room/Client/Player 的 RTTI 名
import re
lo=0x00E00000-LO; hi=min(0x00F00000-LO, len(img))
cur=bytearray(); base_va=0x00E00000
for k in range(lo,hi):
    c=img[k]
    if 32<=c<=126: cur.append(c)
    else:
        if len(cur)>8 and cur[:4]==b'.?AV':
            nm=cur.decode('latin1')
            if any(x in nm for x in ('Room','Client','Player','Lobby','Match','Session')):
                print('   0x%08X  %s' % (base_va+k-len(cur), nm))
        cur=bytearray()
