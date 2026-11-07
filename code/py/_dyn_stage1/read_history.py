from pathlib import Path
import re
root = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
print('=== game3 first records ===')
p = root / r'COD OL\Logs\game3.jsonl'
if p.exists():
    with p.open('r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            print(line.rstrip())
            if i >= 39: break
print('\n=== pe meta ===')
p = root / r'COD OL\scripts\_out\pe_meta_validation.txt'
if p.exists(): print(p.read_text(encoding='utf-8', errors='replace')[:40000])
print('\n=== clean cfg ===')
p = root / r'COD OL\scripts\_out\clean_cfg_reachable.txt'
if p.exists(): print(p.read_text(encoding='utf-8', errors='replace'))
print('\n=== existing remote-relevant logs ===')
roots = [root / r'COD OL\WeGameLauncher\log', root / r'WeGame\log']
pat = re.compile(r'codoMP|Client\.exe|TCLS|command|cmdline|launch', re.I)
for r in roots:
    if not r.exists(): continue
    for f in r.rglob('*'):
        if not f.is_file(): continue
        try: text = f.read_text(encoding='utf-8', errors='ignore')
        except Exception: continue
        if pat.search(text): print(f)
