import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
data = open(os.path.join(D,'r_00CA8000.bin'),'rb').read()
base = 0x00CA8000
def show(va, n=0x120):
    off = va - base
    print('=== 0x%08X ===' % va)
    # 按 \0 切分为可打印串
    chunk = data[off:off+n]
    cur = bytearray(); pos = off
    for ch in chunk:
        if 32 <= ch <= 126:
            cur.append(ch)
        else:
            if len(cur) >= 4:
                print('  0x%08X  %s' % (base+pos-len(cur), cur.decode('latin1')))
            cur = bytearray()
        pos += 1
    if len(cur) >= 4:
        print('  0x%08X  %s' % (base+pos-len(cur), cur.decode('latin1')))
show(0x00DC6700, 0x400)
