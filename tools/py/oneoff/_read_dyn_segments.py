import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def load(name):
 raw=(Path('_dyn_stage1')/name).read_bytes()
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try:return raw.decode(enc).splitlines()
  except UnicodeDecodeError:pass
 return []
for name,ranges in [('runtime_probe.log',[(1,220)]),('runtime_target_probe.log',[(1,230)]),('direct_exe_probe2.log',[(1,120)])]:
 lines=load(name); print('\n===== '+name+f' total={len(lines)} =====')
 for a,b in ranges:
  for i in range(a-1,min(b,len(lines))): print(f'{i+1:05d}: {lines[i]}')
