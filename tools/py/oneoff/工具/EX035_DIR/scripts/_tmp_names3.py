from pathlib import Path
for p in Path('.').iterdir():
    if p.name.lower().startswith('codomp'):
        print(p.name, hex(p.stat().st_size))
