from pathlib import Path
for p in Path('.').iterdir():
    if p.name.lower().startswith('codomp'):
        print(repr(p.name), p.stat().st_size)
