from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
start=s.index('        switch (e->field_offset) {')
end=s.index('        default: known=0; break;',start)
new='''        switch (e->field_offset) {
        case 0x978: def->move_speed_scale=f32v(e->value); break;
        case 0x97c: def->ads_move_speed_scale=f32v(e->value); break;
        case 0x980: def->sprint_duration_scale=f32v(e->value); break;
        case 0x984: def->ads_view_kick_pitch_min=f32v(e->value); break;
        case 0x988: def->ads_view_kick_pitch_max=f32v(e->value); break;
        case 0x98c: def->ads_view_kick_yaw_min=f32v(e->value); break;
        case 0x990: def->ads_view_kick_yaw_max=f32v(e->value); break;
        case 0x994: def->ads_view_scatter_min=f32v(e->value); break;
        case 0x998: def->ads_view_scatter_max=f32v(e->value); break;
        case 0x99c: def->ads_spread=f32v(e->value); break;
        case 0x9a0: def->hip_view_kick_pitch_min=f32v(e->value); break;
        case 0x9a4: def->hip_view_kick_pitch_max=f32v(e->value); break;
        case 0x9a8: def->hip_view_kick_yaw_min=f32v(e->value); break;
        case 0x9ac: def->hip_view_kick_yaw_max=f32v(e->value); break;
        case 0x9b0: def->hip_view_scatter_min=f32v(e->value); break;
        case 0x9b4: def->hip_view_scatter_max=f32v(e->value); break;
        case 0x9b8: def->ads_gun_kick_pitch_min=f32v(e->value); break;
        case 0x9bc: def->ads_gun_kick_pitch_max=f32v(e->value); break;
        case 0x9c0: def->ads_gun_kick_yaw_min=f32v(e->value); break;
        case 0x9c4: def->ads_gun_kick_yaw_max=f32v(e->value); break;
        case 0x9c8: def->ads_gun_kick_accel=f32v(e->value); break;
        case 0x9cc: def->ads_gun_kick_speed_max=f32v(e->value); break;
        case 0x9d0: def->ads_gun_kick_speed_decay=f32v(e->value); break;
        case 0x9d4: def->ads_gun_kick_static_decay=f32v(e->value); break;
        case 0x9d8: def->hip_gun_kick_reduced_kick_bullets=i32v(e->value); break;
        case 0x9dc: def->hip_gun_kick_reduced_kick_percent=f32v(e->value); break;
        case 0x9e0: def->hip_gun_kick_pitch_min=f32v(e->value); break;
        case 0x9e4: def->hip_gun_kick_pitch_max=f32v(e->value); break;
        case 0xe68: def->clip_size=i32v(e->value); break;
        case 0xe6c: /* FMJ/Highcal source-only marker; semantics not yet decoded */ break;
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
s=s[:start]+new+s[end:]
p.write_text(s,encoding='utf-8')
print('patched')
