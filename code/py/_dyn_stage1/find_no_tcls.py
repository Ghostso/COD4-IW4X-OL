from pathlib import Path
for p in list(Path('COD OL').rglob('*')) + list(Path('WeGame').rglob('*')):
    try:
        if not p.is_file() or p.stat().st_size > 120_000_000:
            continue
        b = p.read_bytes()
    except Exception:
        continue
    if b'WIN_NO_TCLS' in b:
        poses = []
        start = 0
        while True:
            i = b.find(b'WIN_NO_TCLS', start)
            if i < 0:
                break
            poses.append(i)
            start = i + 1
        print(p, [hex(x) for x in poses[:20]])
