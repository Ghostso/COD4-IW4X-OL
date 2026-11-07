#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit 03_MASTER_UNRESOLVED_ISSUES.md and 04_P0_CRITICAL_BLOCKERS.md
directly from MASTER_ISSUES.json, so prose counts cannot drift from data.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSED = {"RESOLVED_VERIFIED", "OBSOLETE"}
PRIO_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "NONE": 4}


def load():
    with open(os.path.join(HERE, "MASTER_ISSUES.json"), encoding="utf-8") as f:
        return json.load(f)["issues"]


def table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def header_meta(it):
    return "\n".join([
        "- **系统**: `%s`" % it["system"],
        "- **状态**: `%s`  **优先级**: `%s`  **严重度**: %s" % (it["status"], it["priority"], it["severity"]),
        "- **阻塞可玩战斗**: %s" % ("是" if it.get("blocks_playable") else "否"),
        "- **首次发现**: %s（%s）" % (it.get("first_seen_date", "UNKNOWN"), it.get("first_seen_source", "UNKNOWN")),
        "- **证据等级**: %s" % (it.get("evidence_level") or "UNKNOWN"),
    ])


def detail(it):
    parts = ["### %s — %s\n" % (it["id"], it["title"])]
    parts.append(header_meta(it) + "\n")
    for key, label in [("symptom", "问题现象"), ("expected", "预期行为"), ("actual", "实际行为"),
                       ("trigger", "触发条件"), ("impact", "影响范围"),
                       ("history", "历史调查过程"), ("confidence", "当前最可信判断"),
                       ("missing_evidence", "尚缺证据"), ("minimal_test", "最小验证方法"),
                       ("fix_direction", "推荐修复方向")]:
        v = it.get(key)
        if v:
            parts.append("**%s**：%s\n" % (label, v))
    if it.get("evidence"):
        parts.append("**证据来源**：\n")
        for e in it["evidence"]:
            parts.append("- `%s`" % e)
        parts.append("")
    if it.get("depends_on"):
        parts.append("**依赖**：%s\n" % ", ".join("`%s`" % d for d in it["depends_on"]))
    if it.get("acceptance"):
        parts.append("**完成验收标准**：%s\n" % it["acceptance"])
    parts.append("**复杂度**：%s　**推荐处理顺序**：%s\n" % (it.get("complexity", "UNKNOWN"), it.get("order", "UNKNOWN")))
    parts.append("---\n")
    return "\n".join(parts)


def write_03(issues):
    rows = []
    for it in issues:
        if it["status"] in CLOSED:
            continue
        rows.append([it["id"], it["title"], "`%s`" % it["system"], it["status"], it["priority"],
                     "是" if it.get("blocks_playable") else "否"])
    rows.sort(key=lambda r: (PRIO_ORDER.get(r[4], 9), r[0]))
    doc = ["# 03 — 主未解决问题台账（Master Unresolved Issue Register）\n",
           "> 本文件由 `build_docs.py` 从 `MASTER_ISSUES.json` 直接生成，计数不会与数据脱节。\n",
           "未解决 = 状态不属于 `RESOLVED_VERIFIED` / `OBSOLETE`。当前共 **%d** 项。\n" % len(rows),
           table(rows, ["Issue ID", "标题", "系统", "状态", "优先级", "阻塞可玩"]),
           "\n\n---\n\n## 逐项详情\n"]
    for it in issues:
        if it["status"] in CLOSED:
            continue
        doc.append(detail(it))
    with open(os.path.join(HERE, "03_MASTER_UNRESOLVED_ISSUES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(doc))


def write_04(issues):
    p0 = [it for it in issues if it["priority"] == "P0" and it["status"] not in CLOSED]
    p0.sort(key=lambda x: x["id"])
    head = [
        "# 04 — P0 阻塞项（阻止进入可玩战斗）\n",
        "共 **%d** 项。判定标准：该问题不解决，就无法出现'可操控的游戏画面'。\n" % len(p0),
        "> ★ 关于 'Setting up game / 等待玩家数据'：2026-10-24 已证明它有两个独立成因，",
        "> 一个是快照索引 run 编码（已修复，见 CODOL-ISSUE-0027 的历史），",
        "> 另一个是服务端位置推不动客户端（CODOL-ISSUE-0025，未解决）。",
        "> 但截至 2026-10-29，更前置的问题是**客户端根本不连战斗服**（CODOL-ISSUE-0020），",
        "> 所以本轮 P0 的根节点不是快照，而是'连接不被发起'。\n",
        "## 根阻塞集合\n",
        table([[it["id"], it["title"]] for it in p0], ["Issue ID", "标题"]),
        "\n",
    ]
    body = []
    for it in p0:
        body.append(detail(it))
    with open(os.path.join(HERE, "04_P0_CRITICAL_BLOCKERS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(head) + "\n---\n\n" + "\n".join(body))


def main():
    issues = load()
    write_03(issues)
    write_04(issues)
    print("03/04 written")


if __name__ == "__main__":
    main()
