from pathlib import Path
import re
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
files=list((root/r'COD OL\TCLS').rglob('*.log'))+list((root/r'COD OL\TCLS').rglob('*.txt'))
terms=re.compile(r'codoMP|shipRetail|client\.exe|launch|start|fatal|error|fail|TCLS_SHAREDMEMORY|TASMEMORY|shared',re.I)
out=[]
for p in files:
 try: data=p.read_bytes()
 except: continue
 try:
  if data.startswith(b'\xff\xfe'): text=data.decode('utf-16',errors='replace')
  else: text=data.decode('utf-8',errors='replace')
 except: continue
 hits=[(i+1,l) for i,l in enumerate(text.splitlines()) if terms.search(l)]
 if hits:
  out.append(f'\n===== {p} ({len(hits)} hits) =====')
  for i,l in hits[:300]: out.append(f'{i}: {l}')
Path(root/r'_dyn_stage1\tcls_log_hits.txt').write_text('\n'.join(out),encoding='utf-8')
print('files',len(files),'report',len('\n'.join(out)))
