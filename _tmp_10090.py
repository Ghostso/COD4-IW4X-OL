import os, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5: regs.append((int(p[0],16), int(p[1],16), p[4]))
# 找 ASCII '10090' 以及 u32 小端 0x276A 紧邻 ':' 的 '127.0.0.1:10090'
pats = [b'10090', b'127.0.0.1:10090']
for pat in pats:
    print('===', pat)
    n=0
    for base,size,fn in sorted(regs):
        if not (0x400000 <= base < 0xEA59000): continue
        try: data = open(os.path.join(D,fn),'rb').read()
        except Exception: continue
        i = data.find(pat)
        while i>=0 and n<12:
            va = base+i
            ctx = data[max(0,i-48):i+48]
            print('   0x%08X  %r' % (va, ctx))
            n+=1; i = data.find(pat, i+1)
