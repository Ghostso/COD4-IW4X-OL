import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
data = open(os.path.join(D,'r_034F2000.bin'),'rb').read()
base = 0x034F2000
# GAME_START 命中在 0x037959B5 附近
for center in (0x037959B5, 0x0397C11B):
    off = center - base
    lo = max(0, off-0x300); hi = min(len(data), off+0x300)
    print('=== 0x%08X 附近 ===' % center)
    cur = bytearray(); pos = lo
    for ch in data[lo:hi]:
        if 32 <= ch <= 126:
            cur.append(ch)
        else:
            if len(cur) >= 5:
                print('  0x%08X  %s' % (base+pos-len(cur), cur.decode('latin1')))
            cur = bytearray()
        pos += 1
    print()
