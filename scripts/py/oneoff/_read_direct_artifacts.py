import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
root=Path('_dyn_stage1')
items=[('client_shell_full_disasm.txt',260),('_client_launcher_dis.txt',220),('context_consumer_audit.txt',260),('launch_import_calls_reliable.txt',80),('direct_exe_probe.log',260),('direct_exe_probe2.log',160),('runtime_probe.log',260)]
for name,n in items:
    p=root/name
    print('\n===== '+name+' =====')
    if not p.exists():
        print('MISSING',p); continue
    lines=p.read_text(encoding='utf-8-sig',errors='replace').splitlines()
    for line in lines[:n]: print(line)
    if len(lines)>n: print(f'... truncated {len(lines)-n} more lines')
