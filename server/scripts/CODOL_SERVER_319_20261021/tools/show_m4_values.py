import json
from pathlib import Path
j=json.loads(Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\fixtures\common_mp_weapondefs_20261023.json').read_text(encoding='utf-8'))
r=[x for x in j['firingrange'] if x['name']=='m4a1tech_mp'][0]
for k,v in r.items(): print(k,v)
