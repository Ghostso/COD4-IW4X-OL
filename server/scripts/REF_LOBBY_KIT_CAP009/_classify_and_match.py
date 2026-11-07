# -*- coding: utf-8 -*-
"""补全资源分类, 并与 SKU 目录做匹配。

输入:
    mkt_assets/*.paths.txt            (来自 _extract_marketplace_assets.py)
    marketplace-catalog.json          (启动器内嵌的 37,615 条 SKU)
输出:
    mkt_assets/items_by_category.csv  去重道具名 + 类别 + 是否有图标
    mkt_assets/sku_match.md           匹配结论
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mkt_assets")

# 前缀 -> 类别。带 ★ 的是玩家最关心的"外观/名片"类。
CATEGORY = {
    "pcb": "★名片背景", "pci": "★头像图标", "pcn": "★名片名称",
    "pcf": "★名片边框", "pcab": "★名片动态背景", "pcai": "★名片动态图标",
    "pcaf": "★名片动态边框", "bdg": "★肩章/徽章", "pct": "★称号",
    "cnc": "★解锁类名片",
    "wea": "武器本体/皮肤", "iro": "武器变体", "mag": "弹匣", "muz": "枪口",
    "sco": "瞄具", "gri": "握把", "sto": "枪托", "bar": "枪管", "bip": "两脚架",
    "for": "前握把", "rai": "导轨", "rail": "导轨", "cam": "迷彩", "dec": "挂饰",
    "ret": "准星", "las": "激光", "rof": "射速配件", "stt": "枪托附件",
    "heg": "高爆手雷", "fja": "闪光/震撼", "fpa": "闪光弹", "gre": "手雷",
    "frag": "破片雷", "emp": "电磁雷", "nova": "毒气雷", "wp": "白磷",
    "ves": "防弹衣", "hea": "头盔", "han": "手部/手套", "boo": "靴子",
    "elp": "装备", "eye": "眼睛/面容", "eyes": "眼睛/面容",
    "cha": "角色", "hero": "角色(英雄)", "head": "角色头部",
    "sra": "副武器", "mtl": "近战", "kva": "近战武器", "weaw": "近战武器",
    "knp": "近战配件", "sho": "枪械配件",
    "hud": "HUD", "us": "通用", "codo": "CODOL 专用", "itm": "道具",
    "chg": "充值/礼包", "gift": "礼包", "zom": "僵尸模式", "zm": "僵尸模式",
    "za": "僵尸竞技", "zsc": "僵尸技能", "spy": "间谍模式",
    "perk": "技能", "cst": "技能卡", "cqc": "近战技能",
    "pvp": "PVP", "pve": "PVE", "coop": "合作模式", "sp": "单人",
    "dmz": "DMZ", "td": "TD", "sdp": "SDP", "gm": "游戏模式",
    "logo": "Logo", "word": "文字", "skin": "皮肤材质",
}


def item_name(path):
    n = os.path.basename(path)
    n = re.sub(r"\.(iwi|hlsl|txt|csv)$", "", n)
    n = re.sub(r"_item_icon.*$", "", n)
    n = re.sub(r"_lod\d+.*$", "", n)
    n = re.sub(r"_col.*$|_nml.*$|_spec.*$|_r0.*$", "", n)
    return n.strip("_")


def main():
    allp = set()
    for fn in os.listdir(SRC):
        if not fn.endswith(".paths.txt"):
            continue
        for ln in open(os.path.join(SRC, fn), encoding="utf-8", errors="replace"):
            p = ln.strip()
            if p.startswith("main/"):
                allp.add(p)

    icons = [p for p in allp if "_item_icon" in os.path.basename(p)]
    items = {}
    for p in icons:
        nm = item_name(p)
        if not nm:
            continue
        m = re.match(r"([a-z]{2,4})_", nm)
        pref = m.group(1) if m else ""
        d = items.setdefault(nm, {"name": nm, "prefix": pref,
                                  "category": CATEGORY.get(pref, "其他"),
                                  "icons": 0, "has_model": False})
        d["icons"] += 1

    for p in allp:
        if "/models/" not in p:
            continue
        nm = os.path.basename(p)
        nm = re.sub(r"\.(iwi|hlsl)$", "", nm)
        nm = re.sub(r"_lod\d+.*$", "", nm)
        if nm in items:
            items[nm]["has_model"] = True

    out_csv = os.path.join(SRC, "items_by_category.csv")
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["name", "prefix", "category", "icons", "has_model"])
        w.writeheader()
        for d in sorted(items.values(), key=lambda x: (x["category"], x["name"])):
            w.writerow(d)

    # ---- 与 SKU 目录匹配 ----
    cat = {}
    try:
        for e in json.load(open(os.path.join(ROOT, "marketplace-catalog.json"), encoding="utf-8")):
            cat[int(e["Id"])] = e
    except Exception as e:
        print("catalog 读取失败:", e)

    # catalog 的 Item 值域 vs 资源名无法直接对照(编号体系不同), 这里做**规模对照**
    lines = ["# 资源分类 & SKU 对照", ""]
    lines.append("- 完整版 marketplace 资源(去重): **%d**" % len(allp))
    lines.append("- 其中道具图标 `_item_icon`: **%d**" % len(icons))
    lines.append("- 去重道具名: **%d**" % len(items))
    lines.append("- catalog SKU 条数: **%d**" % len(cat))
    lines.append("")
    lines.append("## 按类别(去重道具名)")
    lines.append("")
    lines.append("| 类别 | 道具数 |")
    lines.append("|---|---|")
    cc = Counter(d["category"] for d in items.values())
    for k, v in cc.most_common():
        lines.append("| %s | %d |" % (k, v))
    lines.append("")
    lines.append("## 外观/名片类明细")
    lines.append("")
    lines.append("| 类别 | 数量 |")
    lines.append("|---|---|")
    for k, v in cc.most_common():
        if k.startswith("★"):
            lines.append("| %s | %d |" % (k, v))
    lines.append("")
    md = os.path.join(SRC, "sku_match.md")
    open(md, "w", encoding="utf-8").write("\n".join(lines))

    print("写出 %s (%d 个道具)" % (out_csv, len(items)))
    print("写出 %s" % md)
    print()
    print("按类别:")
    for k, v in cc.most_common():
        print("  %-22s %6d" % (k, v))


if __name__ == "__main__":
    main()
