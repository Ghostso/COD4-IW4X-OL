import json, re
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json"
j=json.load(open(p,encoding='utf-8'))
syms=j['symbols']
print("sample:",syms[0])
print("total:",len(syms))
def name(s): return s.get('name') or s.get('Name') or str(s)
pats=['chl','chal','bddata','hmac','handshake','netchan','svc_','MSG_','chal']
low=[(s.get('name',''),s.get('value'),s.get('rva')) for s in syms if isinstance(s,dict)]
print("keys of first:",list(syms[0].keys()))
