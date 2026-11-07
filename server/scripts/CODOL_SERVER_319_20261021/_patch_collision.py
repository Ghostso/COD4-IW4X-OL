from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\world\collision.c')
s=p.read_text(encoding='utf-8')
start=s.index('/* 29 script_brushmodel clip volumes')
end=s.index('const int codol_static_box_count')
replacement='''/* Exact script_brushmodel AABBs recovered from the 3.19 ClipMap.\n * The compact clipmap has 30 cbrush_t records; entities *71..*99 map to\n * records 1..29 and are translated by each entity's map origin. */\nconst codol_collision_box_t codol_static_boxes[] = {\n#include "codol_clipmap_coop_train.inc"\n};\n'''
s=s[:start]+replacement+s[end:]
# replace algorithm comment
s=s.replace('/* codol_collision.c -- AABB sweep against the static map collision approximation.\n *\n * Algorithm follows CoD4x cm_trace.c / cm_tracebox.c semantics for an\n * axis-aligned box: per-axis slab clipping against expanded brush bounds,\n * earliest fraction wins, normal taken from the axis that limited the move.\n */', '/* codol_collision.c -- AABB sweep against the verified 3.19 script_brushmodel AABBs.\n *\n * The box set is generated from coop_train_zone.bin by\n * tools/export_clipmap_zone.py. The trace itself follows the axis-aligned\n * slab semantics used by the engine for an AABB sweep.\n */')
p.write_text(s,encoding='utf-8')
print('patched')
