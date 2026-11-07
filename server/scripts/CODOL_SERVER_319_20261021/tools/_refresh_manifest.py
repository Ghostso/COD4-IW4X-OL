from pathlib import Path
import hashlib,json,datetime
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
files=[root/'COD OL'/'main'/'common_mp.ff',root/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin',root/'CODOL_SERVER_319_20261021'/'fixtures'/'coop_train_clipmap_20261023.json',root/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weapondefs_20261023.json',root/'CODOL_SERVER_319_20261021'/'fixtures'/'common_mp_weaponattach_metadata_20261023.json',root/'CODOL_SERVER_319_20261021'/'include'/'codol_clipmap_coop_train.inc',root/'CODOL_SERVER_319_20261021'/'include'/'codol_weapondefs_firingrange.inc']
out={'kind':'static-analysis','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
for p in files:
 out['files'].append({'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
m=root/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'STATIC_ANALYSIS_MANIFEST.json'
m.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print('wrote',m)
