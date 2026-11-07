import sys,pathlib,collections,re
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=pathlib.Path('COD OL/Logs')
for name in ['game2.jsonl','game3.jsonl','t1.jsonl','t2.jsonl','t4.jsonl']:
 p=root/name
 raw=p.read_bytes(); s=None
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try: s=raw.decode(enc); break
  except UnicodeDecodeError: pass
 print('\n===== '+name+' summary =====')
 if not s: print('decode failed'); continue
 c=collections.Counter(); pids=collections.Counter(); ports=collections.Counter(); eps=collections.Counter(); errs=collections.Counter()
 for line in s.splitlines():
  if not line.startswith('{'): continue
  try:o=json.loads(line)
  except:continue
  a=o.get('api') or o.get('note'); c[a]+=1; pids[o.get('pid')]+=1
  if o.get('addr'): eps[str(o.get('addr'))]+=1
  if o.get('port') is not None: ports[str(o.get('port'))]+=1
  if o.get('err') is not None: errs[str(o.get('err'))]+=1
 print('api',c.most_common(30)); print('pid',pids.most_common()); print('addr',eps.most_common(30)); print('port',ports.most_common(30)); print('err',errs.most_common(20))
