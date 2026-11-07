import sys,json,pathlib
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=pathlib.Path('COD OL/Logs')
names=['game2.jsonl','game3.jsonl','t1.jsonl','t2.jsonl','t4.jsonl','t4.txt','gamecap2.txt','gamecap3.txt','_direct_launch_probe.txt','probe1.txt','probe2.txt','target.txt','target3.txt','target_t1.txt','target_t2.txt','target_t4.txt']
for name in names:
 p=root/name
 print('\n===== '+name+' =====')
 if not p.exists(): print('MISSING'); continue
 raw=p.read_bytes(); s=None
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try: s=raw.decode(enc); break
  except UnicodeDecodeError: pass
 if s is None: print('decode failed'); continue
 lines=s.splitlines(); print('lines',len(lines))
 for line in lines[:160]: print(line)
 if len(lines)>160: print('...truncated',len(lines)-160)
