import os, re, struct
p = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin'
b = open(p,'rb').read()
base = 0x00994000
terms = [b'config_mp.cfg', b'config', b'cfg', b'lobby', b'blaze', b'demonware', b'dw', b'dvar',
         b'host', b'port', b'server', b'http', b'iips', b'qos', b'stun', b'net_', b'cl_', b'cg_',
         b'match', b'party', b'master', b'login', b'auth', b'ticket', b'session', b'online',
         b'CODOL', b'codol', b'Tencent', b'tencent', b'qq.com', b'127.0.0.1', b'localhost',
         b'TCP', b'UDP', b'Socket', b'connect']
for t in terms:
    hits=[]
    for m in re.finditer(re.escape(t), b, re.I):
        s=max(0,m.start()-60); e=min(len(b),m.end()+100)
        chunk=b[s:e]
        # printable preview
        prev=''.join(chr(c) if 32<=c<127 else '.' for c in chunk)
        hits.append((base+m.start(), prev))
    if hits:
        print('\n==== %s count=%d' % (t.decode(errors='replace'), len(hits)))
        for va,prev in hits[:20]:
            print('%08x %s' % (va, prev))
