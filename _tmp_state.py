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
    b=rd(va,4)
    return struct.unpack('<I',b)[0] if b and len(b)==4 else None
U=0x3ACA0CD8
print('=== dwRoomMatchUber 状态机 [U+0x20] = %s ===' % ((u32(U+0x20) or 0)))
print('  状态机 0x63C5E0 的跳表: 1->0x63C7F8 2->0x63C85F 3->0x63C89B 4->0x63C8B8 5->0x63C970(自动开局)')
print('  当前=1 => 停在状态 1，未推进到状态 5')
print()
print('=== 状态1 (0x63C7F8) 需要什么 ===')
print('  0x63C7F8  mov eax,[ebp-4] / push eax / mov eax,esi / call 0x63C550')
print('  0x63C803  test al,al / jne 0x63C86E')
print('  0x63C80B  call 0x63C350')
print('  0x63C812  je  0x63C9CA     <- 为假则直接返回')
print()
print('=== 该对象的 +0x24 / +0x28 / +0x2C 是什么 (状态1读的) ===')
for off in (0x20,0x24,0x28,0x2C,0x30,0x34,0x38,0x108,0x120):
    v=u32(U+off)
    print('  +0x%03X = %s' % (off, ('0x%08X'%v) if v is not None else '未覆盖'))
print()
print('=== 该对象的 +0x108 / +0x120 是两个 timer (0xB75D80/0xB75DA0 操作) ===')
for off in (0x100,0x104,0x108,0x10C,0x110,0x120,0x124,0x128,0x12C):
    b=rd(U+off,4)
    if b is None: print('  +0x%03X 未覆盖' % off); continue
    f=struct.unpack('<f',b)[0]
    print('  +0x%03X = %s  (float %.3f)' % (off, b.hex(' '), f))
