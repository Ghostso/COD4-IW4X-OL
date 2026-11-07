import sys,pathlib,json,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
for name in ['game2.jsonl','game3.jsonl','t1.jsonl','t2.jsonl','t4.jsonl']:
 p=pathlib.Path('COD OL/Logs')/name
 raw=p.read_bytes()
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try: s=raw.decode(enc); break
  except UnicodeDecodeError: s=None
 print('\n===== '+name+' =====')
 if s is None: print('decode fail'); continue
 c=collections.Counter(); pids=collections.Counter(); eps=collections.Counter(); errs=collections.Counter(); examples={}
 for line in s.splitlines():
  if not line.startswith('{'): continue
  try:o=json.loads(line)
  except Exception:continue
  a=o.get('api') or o.get('note'); c[a]+=1; pids[str(o.get('pid'))]+=1; eps[str(o.get('ep') or o.get('addr') or o.get('local') or o.get('remote') or '?')]+=1; errs[str(o.get('err'))]+=1; examples.setdefault(a,o)
 print('api',c.most_common(40)); print('pid',pids.most_common()); print('ep',eps.most_common(30)); print('err',errs.most_common(20))
 for a in c:
  print('EX',a,examples[a])
