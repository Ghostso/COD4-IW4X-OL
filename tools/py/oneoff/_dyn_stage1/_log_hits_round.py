from pathlib import Path
roots=[Path(r'WeGame\log'), Path(r'COD OL\WeGameLauncher\log'), Path(r'COD OL\Logs'), Path(r'COD OL\tqm')]
terms=['codoMP_client_shipRetail.exe','StartFor','game_id','29','Stop','stop','维护','停服','fatal','Fatal','error','ERROR','TCLS_SHAREDMEMEMORY','AddGame','LaunchGame','StartGame','game process','game_proc','CreateProcess','RunGame','GameStart']
for root in roots:
    if not root.exists(): continue
    for p in root.rglob('*'):
        if not p.is_file(): continue
        try:
            b=p.read_bytes()
        except Exception: continue
        if not any(t.encode('utf-8','ignore') in b or t.encode('utf-16le') in b for t in terms): continue
        try: s=b.decode('utf-8',errors='replace')
        except: continue
        hits=[]
        for i,line in enumerate(s.splitlines(),1):
            if any(t.lower() in line.lower() for t in terms):
                hits.append((i,line[:1000]))
        if hits:
            print('\n###',p,'size',len(b),'lines',len(s.splitlines()))
            for i,line in hits[-80:]: print(f'{i}: {line}')
