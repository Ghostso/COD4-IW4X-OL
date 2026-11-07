from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weapondefs.h')
s=p.read_text(encoding='utf-8')
s=s.replace('    float location_damage_multipliers[20];\n    float move_speed_scale;\n    float ads_move_speed_scale;\n    float sprint_duration_scale;\n', '    float move_speed_scale;\n    float ads_move_speed_scale;\n    float sprint_duration_scale;\n    float location_damage_multipliers[20];\n')
p.write_text(s,encoding='utf-8')
print('reordered')
