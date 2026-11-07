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
print('=== dwRoomMatchUber 指针槽 [0x082E1518] ===')
b=rd(0x082E1518,4)
if b:
    p=struct.unpack('<I',b)[0]
    print('  [0x082E1518] = 0x%08X' % p)
    if p:
        vb=rd(p,4)
        vt=struct.unpack('<I',vb)[0] if vb else None
        print('  对象 vtable = %s' % (('0x%08X'%vt) if vt else '?'))
        if vt==0x00DC795C: print('  ★ 确认是 dwRoomMatchUber 实例')
        elif vt==0x00DC7274: print('  ★ 是 dwRoomImp 实例(vtable 已被替换?)')
        else: print('  是别的类 vtable')
    else:
        print('  => 为 0：dwRoomMatchUber 从未被创建')
print()
print('=== 对照: dwRoomImp 单例槽 [0x082E13FC] ===')
b=rd(0x082E13FC,4)
print('  [0x082E13FC] = 0x%08X' % struct.unpack('<I',b)[0] if b else '?')
print()
print('=== 其余相邻槽 ===')
for g in (0x082E1510,0x082E1514,0x082E1518,0x082E151C,0x082E1520,0x082E1524,0x082E1558):
    b=rd(g,4)
    print('  [0x%08X] = %s' % (g, ('0x%08X'%struct.unpack('<I',b)[0]) if b else '未覆盖'))
