from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
old='''        case 0xd28: def->max_damage_range=f32v(e->value); break;
        case 0xd50: def->max_damage_range=f32v(e->value); break;
        case 0xd54: def->location_damage_multipliers[4]=f32v(e->value); break;
        case 0xd30: def->min_damage_range=f32v(e->value); break;
        case 0xd58: def->min_damage_range=f32v(e->value); break;
        case 0xd4c: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd74: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;
        case 0xd7c: def->location_damage_multipliers[2]=f32v(e->value); break;
'''
new='''        case 0xd28: def->max_damage_range=f32v(e->value); break;
        case 0xd50: def->max_damage_range=f32v(e->value); break;
        case 0xd30: def->min_damage_range=f32v(e->value); break;
        case 0xd58: def->min_damage_range=f32v(e->value); break;
        case 0xd4c: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd74: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;
        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;
        case 0xd7c: def->location_damage_multipliers[2]=f32v(e->value); break;
'''
if old not in s: raise SystemExit('block not found')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('fixed duplicate')
