#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate the index/report markdown from the full 92-issue database."""
import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    fx = json.load(open(os.path.join(HERE, "ISSUE_FORENSICS.json"), encoding="utf-8"))["issues"]
    return fx


def table(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main():
    fx = load()
    byr = Counter(x["readiness"] for x in fx)
    byp = Counter(x["priority"] for x in fx)
    total = len(fx)

    # ---------------- 00_INDEX
    idx = ["# 00 — CODOL 深度问题取证 · 入口\n",
           "> 任务 `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`　日期 2026-10-29",
           "> **覆盖：全部 %d 条历史 Issue**（原 7 条 P0 + 本轮补齐 85 条）\n" % total,
           "## 一、覆盖与完成度\n",
           table([[k, v] for k, v in sorted(byr.items())], ["fix_readiness", "数量"]) + "\n",
           table([[k, v] for k, v in sorted(byp.items())], ["优先级", "数量"]) + "\n",
           "## 二、登记数与差异说明\n",
           "上一轮台账登记 **92** 条；本轮为 **92** 条全部建档。",
           "任务书提到 79 条未完成，其算式为 92 − 7(P0 已做) − 6(已闭合) = 79；",
           "**本轮的 85 = 92 − 7**，即把 6 条已闭合项（1 RESOLVED_VERIFIED + 5 OBSOLETE）也建立了档案。\n",
           "## 三、文档导航\n",
           "| 文件 | 内容 |", "|---|---|",
           "| `01_EXECUTIVE_TECHNICAL_FINDINGS.md` | 技术结论摘要 |",
           "| `02_FULL_PROJECT_TECHNICAL_HISTORY.md` | 与本批次相关的历史 |",
           "| `03_ROOT_CAUSE_DEPENDENCY_ANALYSIS.md` | 根因与依赖 |",
           "| `04_CRITICAL_PATH_TO_PLAYABLE_BATTLE.md` | 最小可玩关键路径 |",
           "| `05_FIX_READINESS_REPORT.md` | 修复就绪度（全量） |",
           "| `06_MISSING_EVIDENCE_REPORT.md` | 缺失证据 |",
           "| `07_HISTORICAL_REGRESSION_ANALYSIS.md` | 历史回归 |",
           "| `08_FINAL_TECHNICAL_ASSESSMENT.md` | 最终技术评估 |",
           "| `CONNECTION_REGRESSION_DIFFERENTIAL.md` | 10-26 vs 10-29 全差分 |",
           "| `P0_JOINT_ANALYSIS.md` | P0 联合分析 |",
           "| `GAMESTATE_PROTOCOL_FORENSICS.md` / `SNAPSHOT_PROTOCOL_FORENSICS.md` | 协议专项 |",
           "| `UNWIRED_MODULES_FORENSICS.md` | 未接线模块 |",
           "| `NEXT_AGENT_HANDOFF.md` | 可直接接手 |",
           "| `ISSUES/` | %d 份独立档案 |" % total,
           "| `FIX_PACKAGES/` | %d 个 |" % byr.get("FIX_READY", 0),
           "| `INVESTIGATION_PACKAGES/` | %d 个 |" % (byr.get("INVESTIGATION_READY", 0) + byr.get("BLOCKED_BY_EVIDENCE", 0) + byr.get("BLOCKED_BY_DEPENDENCY", 0)),
           "| `*.json` / `*.csv` | 6 个机器可读数据库 |",
           "| `verify_forensics.py` | 自检 |", ""]
    open(os.path.join(HERE, "00_INDEX.md"), "w", encoding="utf-8").write("\n".join(idx))

    # ---------------- 05 readiness report
    rows = []
    for r in sorted(fx, key=lambda x: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3, "NONE": 4}[x["priority"]], x["id"])):
        rows.append([r["id"], r["priority"], "`%s`" % r["readiness"], r["title"][:44]])
    rep = ["# 05 — 修复就绪度报告（全量）\n",
           "> 由 `FIX_READINESS_MATRIX.csv` 汇总。判据：`FIX_READY` 需同时满足根因有证据、已定位代码、",
           "> 方案有技术依据、有可重复验证、有验收标准、已评估对成功基线的影响。\n",
           "## 汇总\n",
           table([[k, v] for k, v in sorted(byr.items())], ["fix_readiness", "数量"]) + "\n",
           "## 逐项\n", table(rows, ["Issue", "优先级", "就绪度", "标题"]), ""]
    open(os.path.join(HERE, "05_FIX_READINESS_REPORT.md"), "w", encoding="utf-8").write("\n".join(rep))

    print("rebuild 00_INDEX / 05")
    for k in sorted(byr):
        print("  %-24s %d" % (k, byr[k]))


if __name__ == "__main__":
    main()
