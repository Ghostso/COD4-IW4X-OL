import json, collections, os, re
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl'
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
print('total hits',len(rows))
c=collections.Counter(r['kw'] for r in rows)
print('keyword counts:')
for k,n in c.most_common(): print('  %-18s %d'%(k,n))
# unique contexts
seen=set(); uniq=[]
for r in rows:
    key=(r['kw'],r['text'])
    if key not in seen:
        seen.add(key); uniq.append(r)
print('unique keyword/context',len(uniq))
# print high value
priority=['config_mp.cfg','lobby','blaze','demonware','dwlobby','server','host','port','iips','qos','stun','ticket','auth','login','session','qq.com','tencent','ace','anticheat','bugtrace','tenproxy','tp3','master','playlist','matchmaking','connect']
for kw in priority:
    hit=[r for r in uniq if r['kw']==kw]
    if not hit: continue
    print('\n===== %s (%d unique) ====='%(kw,len(hit)))
    for r in hit[:25]:
        print('%08x %s'%(r['va'],r['text'][:220]))
