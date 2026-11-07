import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
def load(tag):
    return open(os.path.join(D,tag+'.bin'),'rb').read(), open(os.path.join(D,tag+'_cover.bin'),'rb').read()
def mk(img,cov):
    def rd(va,n):
        o=va-LO
        if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
        return img[o:o+n]
    def u32(va):
        b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
    def f32(va):
        b=rd(va,4); return struct.unpack('<f',b)[0] if b and len(b)==4 else None
    return rd,u32,f32
U=0x3ACA0CD8
print('=== 状态机是否在轮询: 跨快照看 +0x130(计时器) / +0x138 变化 ===')
print('  %-8s %-12s %-14s %-14s %-12s' % ('tag','状态+0x20','+0x130(f)','+0x138','+0x140(f)'))
prev=None
for tag in ('snap_002','snap_003','snap_004'):
    try: img,cov=load(tag)
    except: continue
    rd,u32,f32=mk(img,cov)
    st=u32(U+0x20)
    if st is None or st>10:
        print('  %-8s (对象尚不存在或未初始化)' % tag); continue
    print('  %-8s %-12s %-14s %-14s %-12s' % (tag, st,
        ('%.4f'%f32(U+0x130)) if f32(U+0x130) is not None else '-',
        ('0x%08X'%u32(U+0x138)) if u32(U+0x138) is not None else '-',
        ('%.4f'%f32(U+0x140)) if f32(U+0x140) is not None else '-'))
print()
print('=== 待解: [ebp-8] 那个对象是什么 (判据B 传入的) ===')
print('  状态1 里 0x63C807 mov ecx,[ebp-8] / push ecx / call 0x63C350')
print('  => [ebp-8] 是在函数开头存的局部变量, 来自某个成员')
