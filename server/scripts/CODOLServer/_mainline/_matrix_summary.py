import json,os,glob
root=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
rows=[]
for d in sorted(glob.glob(os.path.join(root,'QOS8081_*'))):
    p=os.path.join(d,'local_listeners.jsonl')
    if not os.path.isfile(p): continue
    ev=[json.loads(l) for l in open(p,encoding='utf-8',errors='replace') if l.strip()]
    p8081=[r for r in ev if r.get('proto')=='udp' and r.get('port')==8081 and r.get('len')]
    qos=[r for r in ev if r.get('sent_qos_len')]
    tqos=[r for r in ev if r.get('sent_reply_len')]
    req=[r for r in ev if r.get('proto')=='udp' and r.get('len')==24]
    rows.append({'dir':os.path.basename(d),'req24':len(req),'tqos_reply':len(tqos),
                 'p8081':len(p8081),'qos_reply':len(qos),
                 'lens':sorted(set(r['len'] for r in p8081))})
for r in rows: print(json.dumps(r,ensure_ascii=False))
tot=sum(r['p8081'] for r in rows)
print('TOTAL 8081 packets across all attempts:',tot)
out=os.path.join(root,'QOS8081_MATRIX_SUMMARY.json')
json.dump(rows,open(out,'w',encoding='utf-8'),indent=2,ensure_ascii=False)
print('wrote',out)
