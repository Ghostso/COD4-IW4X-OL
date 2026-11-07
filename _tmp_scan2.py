import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img): return None
    if sum(cov[o:o+n]) != n: return None
    return img[o:o+n]
def cstr(va,n=80):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
SING=0x3B2BBE80
print('=== 全快照搜 disp32 = 0x10614 的所有出现 (含错位) ===')
pat=struct.pack('<I',0x10614)
n=0
for i in range(len(img)-4):
    if cov[i]!=1: continue
    if img[i:i+4]==pat:
        va=LO+i
        # 前后各 8 字节上下文
        c=img[max(0,i-8):i+12]
        print('   0x%08X  %s' % (va, c.hex(' ')))
        n+=1
        if n>25: break
print('共', n)
print()
print('=== 验证这个区域是否在 image 内 (0x400000..0xEA59000) ===')
print('  例如 .text 里搜 E9/E8 到 0x62FE80 的调用')
# 找所有 call 到闸门B函数
tgt=0x0062FE80
cnt=0
for i in range(0x400000-LO, min(0x0EA59000-LO, len(img)-5)):
    if cov[i]!=1 or img[i]!=0xE8: continue
    rel=struct.unpack_from('<i',img,i+1)[0]
    va=LO+i
    if va+5+rel==tgt:
        print('   call @0x%08X -> 0x%08X' % (va,tgt)); cnt+=1
print('  共', cnt, '处直接 call')
