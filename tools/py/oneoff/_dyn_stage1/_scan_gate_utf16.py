from pathlib import Path
terms=['请使用腾讯游戏登录器','TCLS文件夹内的Client.exe','Client.exe)启动游戏','启动游戏。','腾讯游戏登录器','TCLS文件夹']
for p in Path('.').rglob('*'):
 try:
  if not p.is_file() or p.stat().st_size>300_000_000: continue
  b=p.read_bytes()
 except: continue
 hits=[]
 for t in terms:
  for enc in ('utf-16le','gbk','utf-8'):
   try: needle=t.encode(enc)
   except: continue
   if needle in b: hits.append((t,enc,b.find(needle)))
 if hits: print(p,sorted(set(hits)))
