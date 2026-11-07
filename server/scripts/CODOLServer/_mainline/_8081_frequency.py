import json,os,glob,collections
root=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
# how often does 8081 appear vs. whether a tqos reply was sent?
hits=[]
for d in sorted(glob.glob(os.path.join(root,'*'))):
    p=os.path.join(d,'local_listeners.jsonl')
    if not os.path.isfile(p): continue
    ev=[json.loads(l) for l in open(p,encoding='utf-8',errors='replace') if l.strip()]
    p8081=[r for r in ev if r.get('proto')=='udp' and r.get('port')==8081 and r.get('len')]
    if p8081:
        hits.append((os.path.basename(d),len(p8081),sorted(set(r['len'] for r in p8081))))
print('runs containing 8081 traffic:',len(hits))
for h in hits: print('  %-28s n=%d lens=%s'%h)
