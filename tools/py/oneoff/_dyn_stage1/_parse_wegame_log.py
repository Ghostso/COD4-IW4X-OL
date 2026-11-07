import pathlib, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = pathlib.Path(r'COD OL\WeGameLauncher\log\WegameLauncher.20260913-184748.18620')
patterns = re.compile(r'StartFor|CreateProcess|create process|start process|launch|command|cmd|client\.exe|launcher\.exe|tgp_daemon|wegame\.exe|codoMP|game_id|AddPath', re.I)
for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
    if patterns.search(line):
        print(f'{i}: {line}')
