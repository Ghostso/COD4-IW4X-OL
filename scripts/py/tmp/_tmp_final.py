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
def covok(va,n=4):
    o=va-LO
    return o>=0 and o+n<=len(img) and all(cov[o+k]==1 for k in range(n))
def u32(va):
    b=rd(va,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# MSVC x86 COL 布局: +0 sig, +4 offset, +8 cdOffset, +0xC pTypeDescriptor, +0x10 pClassDescriptor
# 0x00DF86B0 才是 COL 本体 (0x00DF86A8 是别的)
print('=== 直接解析 0x00DF86B0 ===')
for col in (0x00DF86B0, 0x00DF86A8, 0x00DF86F0):
    b=rd(col,20)
    if not b or len(b)<20: print('  0x%08X 不可读'%col); continue
    q=struct.unpack('<IIIII',b)
    print('  0x%08X  sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % ((col,)+q))
    if q[3]:
        print('      TD name = %s' % cstr(q[3]+8,110))
print()
print('=== 从 0x00DC78EC 里的 COL 值重看: 之前读到的是 0x00DF869C ===')
b=rd(0x00DF869C,20)
if b:
    q=struct.unpack('<IIIII',b)
    print('  0x00DF869C  sig=%d off=%d cd=%d pTD=0x%08X pCD=0x%08X' % q)
    print('      TD name = %s' % cstr(q[3]+8,110))
print()
print('=== 结论核对: vtable 0x00DC78F0 是否在任何地方被引用 ===')
pat=struct.pack('<I',0x00DC78F0)
i=img.find(pat,0); n=0
while i>=0:
    if covok(LO+i): print('   引用@0x%08X' % (LO+i)); n+=1
    i=img.find(pat,i+1)
print('   共 %d 处 (只应有 COL 指针那一处)' % n)
