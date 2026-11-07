import os, json, importlib.util
spec=importlib.util.spec_from_file_location('mdscan', r'.\_minidump_scan.py')
md=importlib.util.module_from_spec(spec); spec.loader.exec_module(md)
roots=[r'C:\ProgramData\Microsoft\Windows\WER', os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Windows\WER')]
files=[]
for root in roots:
    if not os.path.isdir(root): continue
    for base,dirs,names in os.walk(root):
        for name in names:
            if name.lower().endswith(('.dmp','.mdmp','.minidump')):
                files.append(os.path.join(base,name))
seen=set(); uniq=[]
for p in sorted(files,key=lambda x:os.path.getsize(x),reverse=True):
    k=os.path.normcase(os.path.abspath(p))
    if k not in seen: seen.add(k); uniq.append(p)
res=[]; matches=[]
for i,p in enumerate(uniq):
    r=md.parse(p); res.append(r)
    ts=[m for m in r['modules'] if (m.get('name') or '').lower().endswith('codomp_client_shipretail.exe')]
    print(f"WER {i+1}/{len(uniq)} size={r['size']} modules={len(r['modules'])} target={len(ts)} err={r['error']} {p}",flush=True)
    for m in ts: print('  TARGET base=0x%X size=0x%X ts=0x%08X %s'%(m['base'],m['size'],m['timestamp'],m['name']),flush=True)
    if ts: matches.append(r)
with open('_wer_scan.json','w',encoding='utf-8') as f: json.dump(res,f,ensure_ascii=False,indent=2)
print('WER_MATCHED_DUMPS',len(matches))
