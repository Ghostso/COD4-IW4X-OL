from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\REVERSE_ENGINEERING_ROADMAP_20261023.md')
s=p.read_text(encoding='utf-8')
old='''### Phase 7：战斗逻辑和世界数据\n\n- 状态：`ACTIVE`\n- 必逆内容：\n'''
new='''### Phase 7：战斗逻辑和世界数据\n\n- 状态：`ACTIVE`\n- 当前进展（2026-10-23）：\n  - ClipMap：已从 3.19 coop zone 闭合 27 planes、4 materials、27 brushsides、30 brushes、30 bounds/contents；29 个 script_brushmodel AABB 已接入碰撞。\n  - WeaponDef：已从 3.19 common_mp XAssetList 定位 1134 个 type-28 资产，恢复 878 个名称和 18 把 firingrange 武器参数。\n  - 产物：`PHASE7_COMBAT_WORLD_INVENTORY_20261023.md`、`fixtures/coop_train_clipmap_20261023.json`、`fixtures/common_mp_weapondefs_20261023.json`。\n- 必逆内容：\n'''
if old not in s: raise SystemExit('phase7 block not found')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('updated roadmap')
