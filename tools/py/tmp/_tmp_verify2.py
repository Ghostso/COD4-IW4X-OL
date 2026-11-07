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
checks = [
 (0x076446B4, 1, '0x808B3C  mov byte [0x76446b4], al'),
 (0x084ABAD7, 1, '0x808B41  mov byte [0x84abad7], 1'),
 (0x0826978C, 4, '0x808B48  mov [0x826978c], esi(=0)'),
 (0x084B3774, 4, '0x808B4E  mov [0x84b3774], 1'),
 (0x0E1F8450, 4, '0x808BCE  mov [0xe1f8450], 0'),
 (0x0C1C85C0, 1, '0x8086FF  byte [0xc1c85c0]=bl'),
 (0x0C1B9DB8, 4, '0x8086F9  [0xc1b9db8]=ebx(0)'),
 (0x0C1B9DBC, 4, '0x808705  [0xc1b9dbc]=ebx(0)'),
 (0x0C1C85C4, 4, '0x808728/30 [0xc1c85c4]'),
 (0x07506265, 1, '0x80877D  byte [0x7506265]=1'),
 (0x082E1394, 4, '0x808771  [0x82e1394]=0'),
 (0x082E1398, 4, '0x808777  [0x82e1398]=0'),
 (0x08534D98, 4, '0x8086C5  [0x8534d98]=2'),
]
print('=== 函数末尾写入的标志 (验证它执行到了最后) ===')
for va,n,label in checks:
    b=rd(va,n)
    if not b:
        print('  0x%08X  未覆盖   %s' % (va,label)); continue
    if n==1:
        print('  0x%08X = 0x%02X    %s' % (va, b[0], label))
    else:
        print('  0x%08X = 0x%08X  %s' % (va, struct.unpack('<I',b)[0], label))
