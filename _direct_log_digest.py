import sys,re
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=Path('_dyn_stage1')
for name in ['direct_exe_probe2.log','runtime_probe.log','runtime_target_probe.log','official_launch_watch2.log']:
 print('\n===== '+name+' =====')
 raw=(root/name).read_bytes()
 s=None
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try: s=raw.decode(enc); break
  except UnicodeDecodeError: pass
 if s is None: print('decode failed'); continue
 lines=s.splitlines()
 for i,line in enumerate(lines):
  if re.search(r'CMI|CREATE|PID=|MODULE| MOD |READ |DLL|Exit|EXIT|FINAL|ERROR|FAIL|NOT|TCLS|TenProxy|Base',line,re.I):
   print(f'{i+1:05d}: {line}')
