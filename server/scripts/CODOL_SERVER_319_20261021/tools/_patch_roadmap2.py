from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\REVERSE_ENGINEERING_ROADMAP_20261023.md')
s=p.read_text(encoding='utf-8')
s=s.replace('  - WeaponDef：已从 3.19 common_mp XAssetList 定位 1134 个 type-28 资产，恢复 878 个名称和 18 把 firingrange 武器参数。\n', '  - WeaponDef：已从 3.19 common_mp XAssetList 定位 1134 个 type-28 资产，恢复 878 个名称和 18 把 firingrange 武器参数；已闭合距离伤害、20 项 hit-location 倍率与头部伤害 API。\n  - WeaponAttach：已索引 259 条 3.19 附件 metadata；3.19 override tuple 布局待反推。\n')
p.write_text(s,encoding='utf-8')
print('roadmap updated')
