from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
a=s.index('        switch (e->field_offset) {')
b=s.index('        default: known=0; break;',a)
cases='''        switch (e->field_offset) {
        case 0x978: def->move_speed_scale=f32v(e->value); break;
        case 0x97c: def->ads_move_speed_scale=f32v(e->value); break;
        case 0x980: def->sprint_duration_scale=f32v(e->value); break;
        case 0xe68: def->clip_size=i32v(e->value); break;
        case 0xe6c: /* source-only marker */ break;
        case 0xe70: def->fire_time_ms=i32v(e->value); break;
        case 0x85c: def->reload_ms=i32v(e->value); break;
        case 0x868: def->reload_empty_ms=i32v(e->value); break;
        case 0x870: def->reload_add_ms=i32v(e->value); break;
        case 0xd10: def->damage=i32v(e->value); break;
        case 0xd14: def->player_damage=i32v(e->value); break;
        case 0xd18: def->min_damage=i32v(e->value); break;
        case 0xd1c: def->min_player_damage=i32v(e->value); break;
        case 0xd28: def->max_damage_range=f32v(e->value); break;
        case 0xd30: def->min_damage_range=f32v(e->value); break;
        case 0xd4c: def->location_damage_multipliers[0]=f32v(e->value); break;
        case 0xd54: def->location_damage_multipliers[2]=f32v(e->value); break;
        case 0xd5c: def->location_damage_multipliers[4]=f32v(e->value); break;
'''
s=s[:a]+cases+s[b:]
p.write_text(s,encoding='utf-8')
print('ok')
