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
def covok(i,n=4): return all(cov[i+k]==1 for k in range(4))
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# MyEventHandler 构造通常写 vtable。搜 'mov [reg], 0x00DC78F0' 形态: C7 00/01/... + imm32
print('=== 搜写 vtable 0x00DC78F0 的指令 (C7 xx F0 78 DC 00) ===')
pat=struct.pack('<I',0x00DC78F0)
i=img.find(pat,0); n=0
while i>=0:
    if covok(i):
        pre=img[max(0,i-2):i]
        print('   0x%08X  前2字节=%s' % (LO+i, pre.hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
# dwRoomMatch::Init 是 static, 可能在 .text 里被调用. 搜 dwRoomMatch vtable/类名引用
print('=== 0x00E6EFA8 ".?AVdwRoomMatch@@" 的 TypeDescriptor 引用 ===')
td = 0x00E6EFA8-8   # pVFTable(4)+spare(4)
print('  推测 TD = 0x%08X' % td)
pat=struct.pack('<I',td)
i=img.find(pat,0); n=0
while i>=0 and n<8:
    if covok(i): print('   0x%08X' % (LO+i)); n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== dwRoomMatch 的 vtable 是哪一个? 找 TD 0x00E6EFA0 的 COL ===')
for va in range(0x00E6EFA0,0x00E6EFB4,4):
    s=cstr(va,60)
    print('   0x%08X  %s' % (va, s or ''))
