import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\MEMDUMP_20261027_v4\mem'
idxs = []
for line in open(os.path.join(D,'regions.txt'), encoding='utf-8', errors='replace'):
    if line.startswith('#'): continue
    p = line.split()
    if len(p) >= 5: idxs.append((int(p[0],16), int(p[1],16), p[4]))
def read_va(va, n):
    for base,size,fn in idxs:
        if base <= va < base+size:
            f=open(os.path.join(D,fn),'rb').read()
            return f[va-base:va-base+n], fn
    return None, None
def cstr(va,n=64):
    b,_=read_va(va,n)
    if not b: return None
    e=b.find(b'\x00')
    return b[:e].decode('latin1') if e>=0 else None
globals_ = {
 0x0849B7D4: 'dvar(2724 类型?)',
 0x0849B7D8: 'dvar(2724)',
 0x0849B7DC: 'dvar(2804)',
 0x0849B7E0: 'dvar(2907)',
 0x0849B7E4: 'dw_autoStartGame',
 0x0849B7A4: 'dw_startGameCountingDown',
 0x0849B7A8: 'dw_lockLobbyCountingDown',
}
for g,label in globals_.items():
    b,fn = read_va(g,4)
    if not b:
        print('  [0x%08X] %-26s 读不到' % (g,label)); continue
    p = struct.unpack('<I', b)[0]
    print('  [0x%08X] %-26s -> 0x%08X' % (g,label,p))
    if p:
        ob,fn2 = read_va(p, 48)
        if ob:
            w = struct.unpack_from('<12I', ob, 0)
            print('      对象 %s: %s' % (fn2, ' '.join('%08X'%x for x in w)))
            nm = cstr(w[0])
            print('        [0]=0x%08X %s' % (w[0], ('"%s"'%nm) if nm else ''))
            for k in (1,2,3,4,5,6,7,8):
                print('        [%d]=0x%08X (%d)  浮点=%s' % (k, w[k], w[k], struct.unpack('<f', struct.pack('<I', w[k]))[0]))
