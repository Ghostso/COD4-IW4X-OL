import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5: regs.append((int(p[0],16), int(p[1],16), p[4]))
names = {
    0x00DDE834: 'dw_autoStartGame',
    0x00DDE848: 'dw_startGameCountingDown',
    0x00DDE8A8: 'dw_enterRoomCountingDown',
    0x00DDE8C4: 'dw_enterGameNextMapCountingDown',
    0x00DDE804: 'dw_refreshGroupCountTime',
}
for va,name in names.items():
    pat = struct.pack('<I', va)
    hits = []
    for base,size,fn in regs:
        try: data = open(os.path.join(D,fn),'rb').read()
        except Exception: continue
        i = data.find(pat)
        while i >= 0:
            hits.append((base+i, fn, i, data))
            i = data.find(pat, i+1)
    print('=== %s @0x%08X : %d 处指针引用' % (name, va, len(hits)))
    for hva, fn, i, data in hits[:8]:
        tail = data[i:i+56]
        print('   指针在 0x%08X (%s+0x%X)' % (hva, fn, i))
        print('      之后 56B: %s' % tail.hex(' '))
    print()
