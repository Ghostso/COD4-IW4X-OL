import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
print('区域数', len(idxs))
TARGETS = [0x0063C8B8, 0x0063C8B0, 0x0063C8C0]
# 1) 作为指针出现（vtable / 函数表）
for t in TARGETS:
    pat = struct.pack('<I', t)
    print('=== 指针 0x%08X ===' % t)
    n=0
    for base,size,fn in idxs:
        try: dd=open(os.path.join(D,fn),'rb').read()
        except: continue
        i=dd.find(pat)
        while i>=0 and n<20:
            print('   0x%08X (%s +0x%X)' % (base+i, fn, i))
            n+=1; i=dd.find(pat,i+1)
    if n==0: print('   无')
# 2) call/jmp rel32 指向它（跨区域边界用相邻区域拼接）
print()
print('=== E8/E9 rel32 指向 0x0063C800..0x0063CA00 ===')
lo,hi=0x0063C800,0x0063CA00
found=[]
# 建立 VA->bytes 拼接：只对含 .text 的区域
import bisect
bases=sorted(idxs)
for base,size,fn in idxs:
    if not (0x400000 <= base < 0x0EA59000): continue
    try: dd=open(os.path.join(D,fn),'rb').read()
    except: continue
    for i in range(len(dd)-5):
        if dd[i] in (0xE8,0xE9):
            rel=struct.unpack_from('<i',dd,i+1)[0]
            tgt=base+i+5+rel
            if lo<=tgt<hi: found.append((base+i, dd[i], tgt, fn))
for a,op,t,fn in found[:25]:
    print('   0x%08X  %s -> 0x%08X' % (a, 'call' if op==0xE8 else 'jmp', t))
print('共', len(found))
