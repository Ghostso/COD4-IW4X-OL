# -*- coding: utf-8 -*-
"""把地图实体表(_map_extract/coop_train_entities.txt)转成 C 表。

产物: include/codol_mapents_coop_train.inc
      include/codol_mapents_coop_train.h(计数)

动机(2026-10-25): 世界已经绑进战斗服(见 main.c 的 bind_world), 但世界里除了玩家
什么都没有 —— 服务端**从未把地图实体生成进去**。这张表就是"地图上到底有什么":
285 个 script_model(道具)、25 个 script_struct、23 个 script_origin、
29 个 script_brushmodel(已经是 clipmap 碰撞, 不再重复生成)、
8+8 个 trigger、**1 个 actor_ally_hero_quartermaster_so(唯一可打的 actor)**。

kind: 0=跳过  1=静态道具(GENERAL)  2=actor(可受伤)
"""
import re
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
SRC = ROOT / "_map_extract" / "coop_train_entities.txt"
OUTINC = ROOT / "CODOL_SERVER_319_20261021" / "include" / "codol_mapents_coop_train.inc"
OUTH = ROOT / "CODOL_SERVER_319_20261021" / "include" / "codol_mapents_coop_train.h"

KIND_SKIP, KIND_PROP, KIND_ACTOR = 0, 1, 2

# 只生成"世界里该有的东西": 道具与 actor。clip(已是碰撞)与 trigger/spawn 跳过。
BY_CLASS = {
    "script_model": KIND_PROP,
    "script_struct": KIND_PROP,
    "script_origin": KIND_PROP,
    "actor_ally_hero_quartermaster_so": KIND_ACTOR,
    "actor_ally_so": KIND_ACTOR,
    "actor_enemy_so": KIND_ACTOR,
    "actor_hero_so": KIND_ACTOR,
    # 明确跳过(保留在统计里, 便于对账)
    "script_brushmodel": KIND_SKIP,
    "trigger_multiple": KIND_SKIP,
    "trigger_once": KIND_SKIP,
    "info_player_start_so": KIND_SKIP,
    "worldspawn": KIND_SKIP,
}


def parse(text):
    out = []
    for b in re.findall(r"\{(.*?)\}", text, re.S):
        def get(key):
            m = re.search(r'"%s"\s+"([^"]*)"' % key, b)
            return m.group(1) if m else ""
        cls = get("classname")
        if not cls:
            continue
        ox, oy, oz = 0.0, 0.0, 0.0
        o = get("origin")
        if o:
            try:
                ox, oy, oz = (float(v) for v in o.split()[:3])
            except ValueError:
                pass
        yaw = 0.0
        a = get("angles")
        if a:
            try:
                yaw = float(a.split()[1])       # angles = "pitch yaw roll"
            except (ValueError, IndexError):
                pass
        out.append((cls, ox, oy, oz, yaw, get("model"), get("targetname")))
    return out


def main():
    ents = parse(SRC.read_text(encoding="utf-8", errors="replace"))
    from collections import Counter
    cnt = Counter(e[0] for e in ents)
    print("实体块总数 = %d" % len(ents))
    for k, v in cnt.most_common():
        print("   %-40s %-4d kind=%s" % (k, v, BY_CLASS.get(k, "未知")))

    rows = [e for e in ents if BY_CLASS.get(e[0], KIND_SKIP) != KIND_SKIP]
    unknown = sorted(set(e[0] for e in ents) - set(BY_CLASS))
    if unknown:
        print("\n⚠ 未登记的 classname(按跳过处理): %s" % unknown)

    lines = []
    for cls, x, y, z, yaw, model, tname in rows:
        k = BY_CLASS[cls]
        lines.append('  { %d, %12.4ff, %12.4ff, %12.4ff, %9.4ff, "%s", "%s", "%s" },'
                     % (k, x, y, z, yaw, cls, model, tname))
    OUTINC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    props = sum(1 for r in rows if BY_CLASS[r[0]] == KIND_PROP)
    actors = sum(1 for r in rows if BY_CLASS[r[0]] == KIND_ACTOR)
    OUTH.write_text(
        "#ifndef CODOL_MAPENTS_COOP_TRAIN_H\n"
        "#define CODOL_MAPENTS_COOP_TRAIN_H\n"
        "/* 由 tools/gen_mapents_inc.py 从 _map_extract/coop_train_entities.txt 生成。\n"
        " * 字段: kind(0=跳过 1=静态道具 2=actor) | origin x,y,z | yaw | classname | model | targetname */\n"
        "#define CODOL_MAPENTS_COOP_TRAIN_COUNT %d\n"
        "typedef struct {\n"
        "    int         kind;\n"
        "    float       x, y, z;\n"
        "    float       yaw;\n"
        "    const char *classname;\n"
        "    const char *model;\n"
        "    const char *targetname;\n"
        "} codol_mapent_t;\n"
        "extern const codol_mapent_t codol_mapents_coop_train[];\n"
        "#endif /* CODOL_MAPENTS_COOP_TRAIN_H */\n" % len(rows), encoding="utf-8")

    print("\n生成 %d 条(静态道具 %d + actor %d)" % (len(rows), props, actors))
    print("  -> %s" % OUTINC.name)
    print("  -> %s" % OUTH.name)


if __name__ == "__main__":
    main()
