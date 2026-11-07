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
print('=== 0xB75DA0 语义确认: {count,freq} 对 ===')
print('  0xB75DA3  mov eax,[esi]')
print('  0xB75DA5  or  eax,[esi+4]')
print('  0xB75DA8  je  0xB75DC2   -> 两个都 0 则直接返回(返回值未设)')
b=rd(0x00B75DC2,8)
print('  0xB75DC2 处:', b.hex(' ') if b else '?')
print()
print('=== 实测 dwRoomMatchUber 的 +0x138 8字节 ===')
b=rd(0x3ACA0CD8+0x138,8)
print('  ', b.hex(' ') if b else '?', ' -> count=0 freq=0 => 空计时器')
print()
print('=== 结论所需的关键旁证: 状态机在跑的话 +0x138 会被写 ===')
print('  0x63C7BD  call 0xB75DA0 (读)')
print('  0x63C7C8  fcomp [0xde7c60]')
print('  0x63C7D5  call 0xB75D90 (★写/重置计时器)')
print('  如果 0x63C5E0 在轮询, 走这条路径就会写 +0x138')
print()
print('=== 检查 0x63C5E0 是否可能从 .tvm0 调用 (搜不到 call 是预期) ===')
print('  已知: 该函数只有 vtable 项引用 0x00DC79C4, 静态 call 数 = 0')
print('  兄弟槽 0x63C0C0/0x63C240/0x63C9F0 静态 call 也全为 0')
print('  => 这一组虚函数全部只经 vtable 分发, 静态找不到驱动者')
