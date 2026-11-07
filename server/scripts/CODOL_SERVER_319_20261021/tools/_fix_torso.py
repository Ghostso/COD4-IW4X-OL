from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
s=s.replace('case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;', 'case 0xd54: def->location_damage_multipliers[4]=f32v(e->value); break;')
p.write_text(s,encoding='utf-8')
print('fixed torso mapping')
