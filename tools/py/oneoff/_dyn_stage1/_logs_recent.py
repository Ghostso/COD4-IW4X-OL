from pathlib import Path
roots = [Path('WeGame/log'), Path('COD OL/WeGameLauncher/log'), Path('COD OL/Logs')]
terms = ['startfor', 'start game', 'startgame', 'launch game', 'launchgame', 'game start', 'run game', 'rungame', 'createprocess', 'codoMP_client_shipRetail', 'tcls_sharedm', 'addgame', 'fetchserverdir', 'game_id: 29', 'game_id:29', 'gameid: 29', 'gameid:29']
for root in roots:
    if not root.exists():
        continue
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        b = p.read_bytes()
        if b.startswith(b'\xff\xfe'):
            text = b.decode('utf-16le', errors='ignore')
        else:
            text = b.decode('utf-8', errors='ignore')
        hits = []
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(t.lower() in low for t in terms):
                hits.append((n, line))
        if hits:
            print('###', p, 'size=', len(b), 'hits=', len(hits))
            for n, line in hits[-160:]:
                print(f'{n}: {line[:1000]}')
