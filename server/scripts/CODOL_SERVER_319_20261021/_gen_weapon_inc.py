from pathlib import Path
import json
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021')
j=json.loads((root/'fixtures'/'common_mp_weapondefs_20261023.json').read_text(encoding='utf-8'))
rows=[]
for r in j['firingrange']:
    rows.append('  {"%s", %d, %d, %d, %d, %d, %d, %d, %d, %d, %.7ff, %.7ff, %.7ff, %.7ff, %.7ff},' % (
        r['name'], r['clip_size'], r['fire_time_ms'], r['reload_ms'], r['reload_empty_ms'], r['reload_add_ms'],
        r['damage'], r['player_damage'], r['min_damage'], r['min_player_damage'],
        r['max_damage_range'], r['min_damage_range'], r['move_speed_scale'], r['ads_move_speed_scale'], r['sprint_duration_scale']))
(root/'include'/'codol_weapondefs_firingrange.inc').write_text('\n'.join(rows)+'\n', encoding='utf-8')
print('wrote', root/'include'/'codol_weapondefs_firingrange.inc')
