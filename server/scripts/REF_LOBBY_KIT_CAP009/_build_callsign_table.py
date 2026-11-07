# -*- coding: utf-8 -*-
"""出"名片 / 称号"专项清单 —— 本地能提供的全集。

覆盖的类别(依据客户端物品类型码 + 资源实际形态):
    pcb  名片背景        pci  头像图标        pcn  名片名称
    pcf  名片边框        pcab 名片动态背景    pcai 名片动态图标
    pcaf 名片动态边框    cnc  解锁类名片      bdg  肩章/徽章
    pct  称号            chg  充值/礼包类名片  itm  道具类名片

输入: mkt_assets/*.paths.txt
输出: mkt_assets/callsign_table.csv / callsign_summary.md
"""
import csv
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mkt_assets")

# 只要这些前缀
WANT = {
    "pcb": "名片背景",
    "pci": "头像图标",
    "pcn": "名片名称",
    "pcf": "名片边框",
    "pcab": "名片动态背景",
    "pcai": "名片动态图标",
    "pcaf": "名片动态边框",
    "cnc": "解锁类名片",
    "bdg": "肩章/徽章",
    "pct": "称号",
    "chg": "礼包类名片",
}


def main():
    if not os.path.isdir(SRC):
        print("缺 %s" % SRC)
        return 1
    paths = set()
    for fn in os.listdir(SRC):
        if not fn.endswith(".paths.txt"):
            continue
        for ln in open(os.path.join(SRC, fn), encoding="utf-8", errors="replace"):
            p = ln.strip()
            if p.startswith("main/"):
                paths.add(p)

    # 按"道具名"聚合: 同一道具可能有 icon / col / nml / lod 多个资源
    items = {}
    for p in paths:
        base = os.path.basename(p)
        m = re.match(r"([a-z]{2,4})_", base)
        if not m or m.group(1) not in WANT:
            continue
        pref = m.group(1)
        # 道具名: 去掉后缀与 lod
        nm = re.sub(r"\.(iwi|hlsl)$", "", base)
        nm = re.sub(r"_item_icon.*$", "", nm)
        nm = re.sub(r"_lod\d+.*$", "", nm)
        nm = re.sub(r"_(col|nml|spec|r0).*$", "", nm)
        nm = nm.strip("_")
        if not nm:
            continue
        d = items.setdefault(nm, {"name": nm, "prefix": pref,
                                  "category": WANT[pref], "files": []})
        d["files"].append(p)

    # 只保留"有 item_icon 的"(= 商城可见道具)
    visible = {k: v for k, v in items.items()
               if any("_item_icon" in f for f in v["files"])}

    out = os.path.join(SRC, "callsign_table.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "prefix", "category", "file_count", "icon_path", "has_model"])
        for k in sorted(visible, key=lambda x: (WANT[visible[x]["prefix"]], x)):
            v = visible[k]
            icon = next((x for x in v["files"] if "_item_icon" in x), "")
            has_model = any("/models/" in x for x in v["files"])
            w.writerow([v["name"], v["prefix"], v["category"],
                        len(v["files"]), icon, "1" if has_model else "0"])

    cat = Counter(v["category"] for v in visible.values())
    md = os.path.join(SRC, "callsign_summary.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 名片 / 称号 —— 本地可提供清单\n\n")
        f.write("- 可见道具(有 `_item_icon`): **%d**\n" % len(visible))
        f.write("- 含全部资源文件条目: %d\n\n" % sum(len(v["files"]) for v in visible.values()))
        f.write("| 类别 | 数量 |\n|---|---|\n")
        for k, v in cat.most_common():
            f.write("| %s | %d |\n" % (k, v))

    print("写出 %s (%d 项)" % (out, len(visible)))
    print("写出 %s" % md)
    print()
    for k, v in cat.most_common():
        print("  %-16s %5d" % (k, v))
    print()
    print("样例(每类前 3):")
    shown = defaultdict(int)
    for k in sorted(visible, key=lambda x: (WANT[visible[x]["prefix"]], x)):
        v = visible[k]
        if shown[v["category"]] < 3:
            shown[v["category"]] += 1
            print("  [%s] %s" % (v["category"], v["name"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
