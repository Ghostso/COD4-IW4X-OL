import json
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=[s for s in j['symbols'] if isinstance(s,dict)]
for kw in ['demonware','dw','bdCore','bdcore','bd_','_bd','lobby','Lobby','dw_','_dw']:
    hits=[s for s in syms if kw.lower() in (s.get('name') or '').lower()]
    print("%-12s %d  %s"%(kw,len(hits),[h['name'] for h in hits[:12]]))
