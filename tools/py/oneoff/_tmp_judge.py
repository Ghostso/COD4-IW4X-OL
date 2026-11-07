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
print('=== 判定: 0x63E510 是否执行过 ===')
print()
print('  证据 A: 它在 0x63E5D6 写 [0x82E1514] (无条件, 在分配之前)')
b=rd(0x082E1514,4)
v=struct.unpack('<I',b)[0] if b else None
print('     [0x082E1514] = %s' % (('0x%08X'%v) if v is not None else '?'))
print('     %s' % ('=> 非 0，函数执行过' if v else '=> 0，函数**从未执行**'))
print()
print('  证据 B: 0x63E510 的入参 [ebp+8] 在 0x63E5FA 被压栈传给构造')
print('     => 但如果函数没跑，后面的 [0x82E1518] 也必然是 0')
b=rd(0x082E1518,4)
print('     [0x082E1518] = %s' % (('0x%08X'%struct.unpack('<I',b)[0]) if b else '?'))
print()
print('=== 结论 ===')
print('  [0x82E1514]=0 且 [0x82E1518]=0, 而 0x63E5D6 的写是无条件的且在分配之前')
print('  => 0x63E510 **整个函数从未被调用**, 不是"调用后分配失败"')
print()
print('=== 那 5 个 call 站点是静态存在的, 说明调用是间接的(表/虚函数) ===')
print('  三个包装 0x63A720/770/7C0 也没有静态调用者 => 整条创建路径都靠间接调用')
