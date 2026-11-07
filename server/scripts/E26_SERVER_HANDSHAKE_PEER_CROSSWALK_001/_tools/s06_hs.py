import json
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=[s for s in j['symbols'] if isinstance(s,dict)]
def show(kw, limit=80):
    hits=[s for s in syms if kw.lower() in (s.get('name') or '').lower()]
    print("=== %s : %d ==="%(kw,len(hits)))
    for s in hits[:limit]: print("   %08X %-40s %s"%(s['rva'],s['name'],s['section']))
for kw in ['_CODOL_Handshake','_CODOL_WriteChallengeResponse','_CODOL_NetchanProcess','_CODOL_Netchan','Handshake','_MSG_Write','_MSG_Read','_MSG_']:
    show(kw)
