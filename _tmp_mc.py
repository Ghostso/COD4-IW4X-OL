import os, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
data = open(os.path.join(D,'r_034F2000.bin'),'rb').read()
base = 0x034F2000
# 这些是 ActionScript 字节码名字池，紧邻的可打印串是它周围的方法名
for center,name in ((0x0397BF9A,'dw_autoStartGame'),(0x0397C2B9,'goGameCountingDown'),(0x0397C2CC,'StartMatchCountDown')):
    off = center-base
    lo=max(0,off-0x180); hi=min(len(data),off+0x180)
    print('=== %s @ 0x%08X ===' % (name, center))
    cur=bytearray(); pos=lo
    for ch in data[lo:hi]:
        if 32<=ch<=126: cur.append(ch)
        else:
            if len(cur)>=4: print('  0x%08X  %s' % (base+pos-len(cur), cur.decode('latin1')))
            cur=bytearray()
        pos+=1
    print()
