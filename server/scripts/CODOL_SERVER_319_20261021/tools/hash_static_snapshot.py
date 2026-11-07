# -*- coding: utf-8 -*-
from pathlib import Path
import hashlib, json
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
project=root/'CODOL_SERVER_319_20261021'
out=root/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'STATIC_ANALYSIS_MANIFEST.json'
paths=[root/'COD OL'/'main'/'common_mp.ff',root/'run_codol_001'/'runs'/'PHASE7_STATIC_20261023'/'common_mp_zone.bin']
for p in [
 project/'fixtures'/'coop_train_clipmap_20261023.json',
 project/'fixtures'/'common_mp_weapondefs_20261023.json',
 project/'fixtures'/'common_mp_weaponattach_metadata_20261023.json',
 project/'fixtures'/'common_mp_weaponattach_records_20261023.json',
 project/'fixtures'/'common_mp_weaponattach_field_census_20261023.json',
 project/'include'/'codol_clipmap_coop_train.inc',
 project/'include'/'codol_weapondefs_firingrange.inc',
 project/'include'/'codol_weaponattach_scalar_firingrange.inc',
 project/'include'/'codol_weaponattach_names.inc',
 project/'include'/'codol_weapondefs.h',
 project/'include'/'codol_weaponattach.h',
 project/'include'/'codol_collision.h',
 project/'include'/'codol_combat.h',
 project/'include'/'codol_projectile.h',
 project/'include'/'codol_gamemode.h',
 project/'include'/'codol_entity.h',
 project/'include'/'codol_player.h',
 project/'include'/'codol_battle_service.h',
 project/'src'/'battle'/'weapondefs.c',
 project/'src'/'battle'/'weaponattach.c',
 project/'src'/'world'/'collision.c',
 project/'src'/'world'/'combat.c',
 project/'src'/'world'/'projectile.c',
 project/'src'/'world'/'gamemode.c',
 project/'src'/'world'/'player.c',
 project/'src'/'entity'/'entity.c',
 project/'src'/'world_assets'/'world.c',
 project/'src'/'movement'/'movement.c',
 project/'src'/'battle'/'battle_service.c',
 project/'src'/'main.c',
 project/'tests'/'test_weapondefs.c',
 project/'tests'/'test_static_closure.c',
 project/'tools'/'export_weapondefs.py',
 project/'tools'/'export_weaponattach_records.py',
 project/'tools'/'weaponattach_field_census.py',
 project/'tools'/'update_attach_scalars.py',
 project/'tools'/'hash_static_snapshot.py',
 project/'docs'/'REVERSE_ENGINEERING_ROADMAP_20261023.md',
 project/'docs'/'PHASE7_COMBAT_WORLD_INVENTORY_20261023.md',
 project/'docs'/'INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md',
]: paths.append(p)
files=[]
for p in paths:
 if not p.exists(): raise SystemExit('missing '+str(p))
 files.append({'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
out.write_text(json.dumps({'kind':'static-analysis','files':files},indent=2,ensure_ascii=False),encoding='utf-8')
print('files',len(files),'wrote',out)
