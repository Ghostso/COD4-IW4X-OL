from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_COMBAT_WORLD_INVENTORY_20261023.md')
s=p.read_text(encoding='utf-8')
s=s.replace('3. 命中盒、hit location multiplier、护甲/穿透和伤害衰减公式。', '3. 角色命中盒几何、护甲/穿透；武器侧距离伤害和 hit-location multiplier 已闭合。')
p.write_text(s,encoding='utf-8')
print('patched')
