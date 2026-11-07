from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_collision.h')
s=p.read_text(encoding='utf-8')
s=s.replace(' * This is an axis-aligned approximation of the brush set. It is deliberately\n * conservative: the exact cbrush_t side planes are parsed separately\n * (tools/clipmap_locate.py) but not yet converted into trace planes.\n', ' * The 29 script_brushmodel volumes are exact AABBs from the 3.19 ClipMap\n * (tools/export_clipmap_zone.py); the eight plane-backed world brushes are\n * retained in the JSON evidence but are not used by this movement trace yet.\n')
p.write_text(s,encoding='utf-8')
print('patched collision.h')
