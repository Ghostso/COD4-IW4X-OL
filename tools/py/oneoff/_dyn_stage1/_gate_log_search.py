from pathlib import Path
ROOT=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
terms=['WIN_NO_TCLS','IsTCLSLogOn','请使用腾讯游戏登录器']
files=[]
for p in ROOT.rglob('*'):
 if not p.is_file(): continue
 if p.suffix.lower() in ('.log','.txt','.ini','.json','.out','.xml','.csv'):
  files.append(p)
for term in terms:
 print('\n===',term,'===')
 c=0
 for p in files:
  try:
   if p.stat().st_size>80_000_000: continue
   b=p.read_bytes()
  except: continue
  found=False
  for enc in ('utf-8-sig','utf-16le','gbk'):
   try: s=b.decode(enc)
   except: continue
   if term in s:
    for i,l in enumerate(s.splitlines()):
     if term in l:
      print(p.relative_to(ROOT),'line',i+1,l[:500]); c+=1
      if c>=30: break
    if c>=30: break
  if c>=30: break
 print('count_shown',c)
