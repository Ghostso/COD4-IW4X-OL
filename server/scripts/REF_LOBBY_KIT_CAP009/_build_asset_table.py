# -*- coding: utf-8 -*-
"""把 37 个完整版 common_marketplace 包抽出的资源清单, 整理成结构化表格。

输入: _extract_marketplace_assets.py 产出的 mkt_assets/*.paths.txt
输出:
    mkt_assets/mkt_assets_table.csv   每条资源一行
    mkt_assets/mkt_assets_summary.md  按类别汇总

★ 意义: 这些是**客户端真实会加载的资源**, 比启动器内嵌的 catalog 更权威。
  文件名前缀就是 exe 里的物品类型码(wea=武器本体, pcb=名片背景, pci=头像图标,
  bdg=肩章, pct=称号, mag=弹匣, muz=枪口, sco=瞄具, gri=握把, ...)。
"""
import csv
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "mkt_assets")

CATEGORY = {
    "wea": "武器本体/皮肤",
    "iro": "武器变体(iron)",
    "mag": "弹匣",
    "muz": "枪口",
    "sco": "瞄具",
    "gri": "握把",
    "sto": "枪托",
    "bar": "枪管",
    "bip": "两脚架",
    "for": "前握把",
    "rai": "导轨",
    "cam": "迷彩",
    "dec": "挂饰",
    "ret": "准星",
    "pcb": "名片背景",
    "pci": "头像图标",
    "pcn": "名片(名称)",
    "pcf": "名片边框",
    "pcab": "名片(动态背景)",
    "pcai": "名片(动态图标)",
    "pct": "称号",
    "bdg": "肩章/徽章",
    "cha": "角色",
    "hud": "HUD",
    "heg": "高爆手雷",
    "fja": "闪光/震撼",
    "fpa": "闪光弹",
    "ves": "防弹衣/背心",
    "hea": "头盔",
    "elp": "装备",
    "eye": "眼睛/面容",
    "boo": "靴子",
    "mtl": "近战",
    "gre": "手雷",
    "sra": "副武器",
    "kva": "近战武器",
    "spy": "间谍模式",
    "codo": "CODOL 专用",
    "us": "通用",
}


def main():
    if not os.path.isdir(SRC):
        print("缺 %s —— 先跑 _extract_marketplace_assets.py" % SRC)
        return 1
    rows = []
    per_pack = Counter()
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".paths.txt"):
            continue
        pack = fn[:-len(".paths.txt")]
        for ln in open(os.path.join(SRC, fn), encoding="utf-8", errors="replace"):
            p = ln.strip()
            if not p.startswith("main/"):
                continue
            kind = "images" if "/images/" in p else ("models" if "/models/" in p else "other")
            base = os.path.basename(p)
            base = re.sub(r"\.(iwi|hlsl|txt|csv)$", "", base)
            base = re.sub(r"_lod\d+(_|$)", "_", base).strip("_")
            m = re.match(r"([a-z]{2,4})_", base)
            pref = m.group(1) if m else ""
            rows.append({"path": p, "kind": kind, "prefix": pref,
                         "category": CATEGORY.get(pref, ""), "item": base, "pack": pack})
            per_pack[pack] += 1

    out_csv = os.path.join(SRC, "mkt_assets_table.csv")
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["path", "kind", "prefix", "category", "item", "pack"])
        w.writeheader()
        w.writerows(rows)

    uniq = {}
    for r in rows:
        uniq.setdefault(r["path"], r)
    cat = Counter()
    for r in uniq.values():
        cat[r["category"] or ("(未分类:%s)" % (r["prefix"] or "无前缀"))] += 1

    md = os.path.join(SRC, "mkt_assets_summary.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("# 完整版 common_marketplace 资源清单\n\n")
        f.write("- 资源路径(去重): **%d**\n" % len(uniq))
        f.write("- 原始条目: %d\n" % len(rows))
        f.write("- 来源包: %d 个\n\n" % len(per_pack))
        f.write("## 按类别\n\n| 类别 | 资源数 |\n|---|---|\n")
        for k, v in cat.most_common():
            f.write("| %s | %d |\n" % (k, v))
        f.write("\n## 按来源包\n\n| 包 | 资源数 |\n|---|---|\n")
        for k, v in per_pack.most_common():
            f.write("| %s | %d |\n" % (k, v))

    print("写出 %s (%d 行)" % (out_csv, len(rows)))
    print("写出 %s" % md)
    print()
    for k, v in cat.most_common(30):
        print("  %-24s %6d" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
