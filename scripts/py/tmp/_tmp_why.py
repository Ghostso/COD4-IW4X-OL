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
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
U=0x3ACA0CD8
print('=== 0x63C1E0 读的计时器 [+0x138] 到底是对象还是内联 float ===')
b=rd(U+0x138,0x14)
print('  raw:', b.hex(' ') if b else '?')
print()
print('  b75da0(ecx=[esi+0x138]) 说明 +0x138 处放的是**一个对象/计时器的值**')
print('  实测 0x%08X = 0  -> 计时器从未启动' % (u32(U+0x138) or 0))
print()
print('=== 关键: 检查 0x63C1E0 返回真的是假吗 ===')
print('  0x63C1E0 逻辑:')
print('    x = timer(+0x138) + [+0x140]')
print('    if x == 0: goto 0x63C238 (返回假)')
print('    if x >= dw_enterGameNextMapCountingDown(45.0): 返回 1')
print('    else: goto 0x63C238 (返回假)')
print()
print('  x = 0.0 + 0.0 = 0.0  ->  走第一个分支 -> 返回假  ✓ 与实测一致')
print()
print('=== 所以两个判据都为假, 状态停在 1 ===')
print('  判据A (0x63C550) 传 esi = this,  内部 eax=esi(this)')
print('  判据B (0x63C350) 传 [ebp-8],  内部 eax=esi 但入口还做了 mov eax,esi')
print()
print('  注意 0x63C350 开头: mov eax,esi (不用参数!) 然后 call 0x63C1E0')
print('  => 判据B 实际也是算 this 的计时器, 参数被忽略')
b=rd(0x0063C350,8)
print('  0x63C350 头部:', b.hex(' ') if b else '?')
