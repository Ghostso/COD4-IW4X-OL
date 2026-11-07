import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
for name in ['direct_exe_probe.log','direct_exe_probe2.log','runtime_probe.log','runtime_target_probe.log']:
 print('\n===== '+name+' =====')
 raw=(Path('_dyn_stage1')/name).read_bytes()
 for enc in ['utf-8-sig','utf-16-le','gb18030']:
  try:
   s=raw.decode(enc)
   print('[encoding]',enc)
   print(s)
   break
  except UnicodeDecodeError: pass
