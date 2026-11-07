import os, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5:
        regs.append((int(p[0],16), int(p[1],16), p[4]))
hits = []
for base,size,fn in sorted(regs):
    if not (0x400000 <= base < 0xEA59000): continue
    try: data = open(os.path.join(D,fn),'rb').read()
    except Exception: continue
    for m in re.finditer(rb'[\x20-\x7e]{6,80}', data):
        s = m.group(0)
        if b'coop' in s.lower():
            hits.append((base+m.start(), s.decode('latin1')))
print('coop 串命中', len(hits))
seen=set()
for va,s in hits:
    if s in seen: continue
    seen.add(s)
    print('  0x%08X  %s' % (va, s))
    if len(seen) >= 70: break
