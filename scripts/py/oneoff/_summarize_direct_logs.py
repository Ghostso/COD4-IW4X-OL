import sys,pathlib,re,json,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=pathlib.Path('COD OL/Logs')
names=['game2.jsonl','game3.jsonl','t1.jsonl','t2.jsonl','t4.jsonl','gamecap2.txt','gamecap3.txt','_direct_launch_probe.txt','mod13596.txt','poll3_console.txt','etwtest.txt','etwtest2.txt']
for name in names:
 p=root/name
 print('\n===== '+name+' =====')
 if not p.exists(): print('MISSING'); continue
 raw=p.read_bytes(); s=None
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try: s=raw.decode(enc); break
  except UnicodeDecodeError: pass
 if s is None: print('decode failed'); continue
 lines=s.splitlines()
 # summarize JSON-ish records
 if name.endswith('.jsonl'):
  c=collections.Counter(); pids=collections.Counter(); first=[]; last=[]
  for line in lines:
   try: o=json.loads(line)
   except Exception: continue
   c[o.get('api') or o.get('note') or o.get('kind') or '?']+=1
   if o.get('pid') is not None: pids[str(o.get('pid'))]+=1
   if len(first)<12: first.append(o)
   last=(last+[o])[-12:]
  print('json_lines',len(lines),'apis',c.most_common(30),'pids',pids.most_common(20))
  print('FIRST'); [print(x) for x in first]
  print('LAST'); [print(x) for x in last]
 else:
  print('lines',len(lines))
  for line in lines[:100]: print(line)
  if len(lines)>100: print('...truncated',len(lines)-100)
