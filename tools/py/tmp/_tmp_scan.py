import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
regs = {}
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5:
        regs[int(p[0],16)] = (int(p[1],16), p[4])
print('regions:', len(regs))
# 全局搜几种关键串
targets = [b'dwRoomMessageStartGame', b'ChannelSubscriptionFail', b'sv_resetServer',
           b'coop_training_mp_cargoship', b'mmstart', b'GAME_START', b'CreateRoom']
found = {t: [] for t in targets}
for base,(size,fn) in regs.items():
    fp = os.path.join(D, fn)
    try: data = open(fp,'rb').read()
    except Exception: continue
    for t in targets:
        i = data.find(t)
        while i >= 0 and len(found[t]) < 6:
            found[t].append((base+i, fn, i)); i = data.find(t, i+1)
for t in targets:
    print()
    print(t.decode(), '->', len(found[t]), '命中')
    for va,fn,off in found[t][:6]:
        print('   0x%08X  %s +0x%X' % (va, fn, off))
