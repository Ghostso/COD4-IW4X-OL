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
print('=== 验证函数确实执行完了：末尾写入的标志 ===')
checks = [
 (0x076446B4, 1, 'mov byte [0x76446b4], al  (0x808B3C)'),
 (0x084ABAD7, 1, 'mov byte [0x84abad7], 1     (0x808B41/0x808BAB)'),
 (0x0826978C, 4, 'mov [0x826978c], esi=0     (0x808B48)'),
 (0x084B3774, 4, 'mov [0x84b3774], 1         (0x808B4E)'),
 (0x0E1F8450, 4, 'mov [0xe1f8450], 0         (0x808BCE)'),
 (0x0C1C85C0, 1, 'byte [0xc1c85c0]=bl=0      (0x8086FF)'),
 (0x0C1B9DB8, 4, 'mov [0xc1b9db8], ebx=0     (0x8086F9)'),
 (0x0C1B9DBC, 4, 'mov [0xc1b9dbc], ebx=0     (0x808705)'),
 (0x0C1C85C4, 4, 'mov [0xc1c85c4], esi/ebx   (0x808728/0x808730)'),
 (0x07506265, 1, 'mov byte [0x7506265], 1    (0x80877D)'),
 (0x082E1394, 4, 'mov [0x82e1394], ebx=0     (0x808771)'),
 (0x082E1398, 4, 'mov [0x82e1398], ebx=0     (0x808777)'),
 (0x08534D98, 4, 'mov [0x8534d98], 2         (0x8086C5)'),
]
for va,n,label in checks:
    b=rd(va,n)
    if not b:
        print('  0x%08X  %-40s 未覆盖' % (va,label)); continue
    v = b[0] if n==1 else struct.unpack('<I',b)[0]
    print('  0x%08X = 0x%0*X  %-40s' % (va, v, n*2, label))
print()
print('=== 0x808717 那个分支依赖的值: call 0xb74220 的返回 ===')
print('  存到了 [0xc1c85c4]:')
b=rd(0x0C1C85C4,4)
print('    0x%08X = %s' % (0x0C1C85C4, struct.unpack('<I',b)[0] if b else '未覆盖'))
