import json
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=[s for s in j['symbols'] if isinstance(s,dict)]
def show(kw, limit=60):
    hits=[s for s in syms if kw.lower() in (s.get('name') or '').lower()]
    print("=== %s : %d ==="%(kw,len(hits)))
    for s in hits[:limit]: print("   %08X %s"%(s['rva'],s['name']))
for kw in ['chal','CHALLENGE','bddata','hmac','handshake','netchan','svc_','MSG_Write','_MSG_','SV_WriteReliable','SV_WriteGamestate','SV_WriteSnapshot','SV_WriteConfigstrings']:
    show(kw)
