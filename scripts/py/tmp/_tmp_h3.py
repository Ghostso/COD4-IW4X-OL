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
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 0x63B500 是 MyEventHandler 的虚函数。Init 创建它 -> 必然写 vtable 0xDC78F0 或
# 至少调用它的构造。搜 'call 0x63B5xx' 附近区域, 或搜 0x63B500 的 call
# 反过来: MyEventHandler 构造会写 [obj]=0xDC78F0. 用完整 4 字节搜索已做过=0.
# 说明构造里可能是 mov eax,0xDC78F0; mov [ecx],eax  或 lea
print('=== 搜 0xDC78F0 的低位形态: 是否以 mov reg, imm 形式出现 ===')
pat=struct.pack('<I',0x00DC78F0)
i=img.find(pat,0); n=0
while i>=0:
    if all(cov[i+k]==1 for k in range(4)):
        va=LO+i
        pre=img[max(0,i-3):i]
        print('   0x%08X  前3字节=%s' % (va, pre.hex(' ')))
        n+=1
    i=img.find(pat,i+1)
print('   共',n)
print()
print('=== 换思路: 找 dwRoomMatch::Init 的字符串/其他线索 ===')
for s in (b'dwRoomMatch', b'room.match', b'MyEventHandler'):
    i=img.find(s,0)
    cnt=0
    while i>=0 and cnt<8:
        if all(cov[i+k]==1 for k in range(len(s))):
            s2=cstr(LO+i,90)
            if s2: print('   %r @0x%08X -> %s' % (s,LO+i,s2[:80])); cnt+=1
        i=img.find(s,i+1)
