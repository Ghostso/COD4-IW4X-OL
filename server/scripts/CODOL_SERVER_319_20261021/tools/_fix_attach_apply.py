from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
# Add e6c mapping for highcal/fmj record and test-safe offset.
s=s.replace('case 0xe70: def->fire_time_ms=i32v(e->value); break;', 'case 0xe6c: /* highcal/fmj source-only record, no decoded struct field yet */ break;\n        case 0xe70: def->fire_time_ms=i32v(e->value); break;')
s=s.replace('case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;', 'case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;\n        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;')
p.write_text(s,encoding='utf-8')
print('patched e6c')
