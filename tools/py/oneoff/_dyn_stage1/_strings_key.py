import re
from pathlib import Path
terms=[b'StartFor',b'AddGame',b'StartGame',b'LaunchGame',b'RunGame',b'TCLS_SHAREDMEMEMORY',b'TenProxy',b'game_id',b'gameID',b'TCLS_TENPROXY_RESULT',b'GMAE_EXIT',b'tcls_core',b'FetchServerDirForTgp',b'RecvLoginInfo']
for p in [Path(r'WeGame\tgp_daemon.exe'),Path(r'WeGame\tcls\tcls_core.exe'),Path(r'COD OL\TenProxy.dll'),Path(r'COD OL\TCLS\Client.exe'),Path(r'COD OL\WeGameLauncher\launcher.exe')]:
 b=p.read_bytes(); print('\n###',p,len(b))
 for t in terms:
  pos=[]; start=0
  while True:
   i=b.find(t,start)
   if i<0: break
   pos.append(i); start=i+1
  if pos: print(t.decode(),len(pos),[hex(x) for x in pos[:30]])
