import json
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=[s for s in j['symbols'] if isinstance(s,dict)]
for kw in ['clc_','clc','netfield','NetField','svc_bad','svc_','clientCommand','ClientCommand','usercmd','UserMove','lastExecutedCommand','reliableAck','reliable']:
    hits=[s for s in syms if kw.lower() in (s.get('name') or '').lower()]
    print("=== %s : %d ==="%(kw,len(hits)))
    for h in hits[:18]: print("   %08X %s"%(h['rva'],h['name']))
