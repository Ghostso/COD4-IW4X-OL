import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs=[]
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p=line.split()
    if len(p)>=5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
hits=[]
for pat,name in ((struct.pack('<I',0x0849B7A4),'dw_autoStartGame 句柄'),
                 (struct.pack('<I',0x0849B7A8),'dw_startGameCountingDown 句柄')):
    print('===', name)
    for base,size,fn in idxs:
        if not (0x400000 <= base < 0x0EA59000): continue
        try: data=open(os.path.join(D,fn),'rb').read()
        except: continue
        i=data.find(pat)
        while i>=0:
            print('   0x%08X (%s+0x%X)' % (base+i, fn, i))
            i=data.find(pat,i+1)
