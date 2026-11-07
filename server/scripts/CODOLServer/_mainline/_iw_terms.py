import re
b=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin','rb').read()
base=0x00994000
# search likely IW4/CODOL identifiers in ASCII and UTF-16
terms=['config_mp','config.cfg','iw4','gsc','hks','dvar','dwlobby','blaze','demonware','lobby','party','matchmaking','playlist','fastfile','zone','onlinegame','title_id','dw_config','nfs','account','ticket','profile','stats','challenge','rank','server','master']
for t in terms:
    for enc,pat in [('ascii',t.encode()),('utf16',t.encode('utf-16-le'))]:
        hits=list(re.finditer(re.escape(pat),b,re.I))
        if hits:
            print('%-12s %-5s %d %s' % (t,enc,len(hits),[hex(base+m.start()) for m in hits[:10]]))
