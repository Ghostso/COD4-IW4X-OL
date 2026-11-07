import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5: regs.append((int(p[0],16), int(p[1],16), p[4]))
targets = [b'dw_autoStartGame', b'dw_startGameCountingDown', b'dw_enterRoomCountingDown']
for t in targets:
    print('===', t.decode())
    for base,size,fn in sorted(regs):
        if not (0x400000 <= base < 0x2300000): continue
        try: data = open(os.path.join(D,fn),'rb').read()
        except Exception: continue
        i = data.find(t)
        while i >= 0:
            va = base + i
            # 看它附近是否有值（dvar 结构里名字后面常跟值）
            ctx = data[max(0,i-40):i+len(t)+60]
            print('   0x%08X  ctx=%r' % (va, ctx))
            i = data.find(t, i+1)
            if i > 0 and va > 0x2300000: break
