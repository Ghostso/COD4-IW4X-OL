from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8').replace('        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;\n        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;\n','        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;\n')
p.write_text(s,encoding='utf-8')
