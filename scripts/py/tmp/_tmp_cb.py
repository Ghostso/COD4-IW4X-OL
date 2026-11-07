import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
print('=== 找 0x63C8xx/0x63C9xx 附近的函数入口及其引用 ===')
# 从 0x63C900 往前找函数序言 (55 8B EC / 8B FF 55 8B EC / 53 8B ...)
data,_ = None, None
for base,size,fn in idxs:
    if base <= 0x0063C000 < base+size:
        data=open(os.path.join(D,fn),'rb').read(); fbase=base; ffn=fn; break
o = 0x0063C900 - fbase
# 打印前 0xC0 字节找序言
for i in range(0xC0, 0, -1):
    va = 0x0063C900 - i
    b = data[o-i:o-i+4]
    if b[:1] == b'\x55' and b[1:2]==b'\x8b' and b[2:3]==b'\xec':
        print('  函数序言 55 8B EC @ 0x%08X' % va); break
    if b[:2] == b'\x8b\xff' and b[2:3]==b'\x55' and b[3:4]==b'\x8b':
        print('  函数序言 8B FF 55 8B @ 0x%08X' % va); break
# 搜 rel32 调用到 0x63C8xx 区间
import struct as st
for target in (0x0063C8E0, 0x0063C8F0, 0x0063C900, 0x0063C910):
    pat = st.pack('<I', (target - 0x63C8E0) & 0xFFFFFFFF)
print()
print('=== 在 .text 里搜 call rel32 指向 0x63C8xx..0x63C9xx ===')
lo, hi = 0x0063C800, 0x0063CA00
found=[]
for base,size,fn in idxs:
    if not (0x400000 <= base < 0x0EA59000): continue
    dd=open(os.path.join(D,fn),'rb').read()
    for i in range(len(dd)-5):
        if dd[i]==0xE8:
            rel=st.unpack_from('<i', dd, i+1)[0]
            tgt = base+i+5+rel
            if lo <= tgt < hi:
                found.append((base+i, tgt, fn))
for a,t,fn in found[:20]:
    print('   0x%08X  call -> 0x%08X  (%s)' % (a,t,fn))
print('共', len(found))
