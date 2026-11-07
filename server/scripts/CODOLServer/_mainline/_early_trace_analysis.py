import json, collections
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_EARLY_20260925_113543\engine\early_trace.jsonl'
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
print('rows',len(rows),'duration',rows[-1]['t'])
for name in ['engine_head','engine_code','sentinel','runtime_strings','libcurl']:
    nz=[r for r in rows if r[name]['nz']>0]
    prot=collections.Counter((r[name]['state'],r[name]['protect']) for r in rows)
    got=collections.Counter(r[name]['got'] for r in rows)
    print('\n',name,'nonzero rows',len(nz),'got',got,'protect',prot)
    if nz:
        for r in nz[:10]: print('  t',r['t'],r[name])
# any page ever nonzero
for r in rows:
    for name in ['engine_head','engine_code','sentinel','runtime_strings','libcurl']:
        if r[name]['nz']:
            print('ANY',r['t'],name,r[name]); raise SystemExit
print('NO NONZERO IN ANY PROBE')
