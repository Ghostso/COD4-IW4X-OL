from pathlib import Path
names=[r'COD OL\WeGameLauncher\config\Launcher.json',r'COD OL\WeGameLauncher\config\Launcher_remote.json',r'COD OL\WeGameLauncher\config\Game.json',r'COD OL\WeGameLauncher\Tenio.ini',r'COD OL\TCLS\Tenio.ini',r'COD OL\TCLS\version.ini',r'COD OL\TCLS\config\VersionServerConfig.xml',r'COD OL\TCLS\config\dirserver.xml',r'COD OL\TCLS\config\commonconfig.cfg']
out=[]
for n in names:
    p=Path(n)
    out.append('\n===== '+n+' =====')
    out.append(p.read_text(encoding='utf-8',errors='replace') if p.exists() else 'MISSING')
Path(r'_dyn_stage1\config_dump.txt').write_text('\n'.join(out),encoding='utf-8')
print('WROTE',len('\n'.join(out)))
