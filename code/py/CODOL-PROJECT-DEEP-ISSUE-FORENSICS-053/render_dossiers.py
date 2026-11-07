#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render 22-section dossiers from per-issue data dicts.

Usage:  python -I render_dossiers.py
Reads _data_p1_*.py / _data_p2_*.py / _data_p3_*.py and writes ISSUES/<id>.md
Sections that are not applicable are marked NOT_APPLICABLE with a reason.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ISSUES")
REG = os.path.join(os.path.dirname(HERE), "CODOL-PROJECT-GLOBAL-UNRESOLVED-ISSUES-AUDIT", "MASTER_ISSUES.json")


HANDWRITTEN = {"CODOL-ISSUE-0020","CODOL-ISSUE-0021","CODOL-ISSUE-0074","CODOL-ISSUE-0012",
               "CODOL-ISSUE-0009","CODOL-ISSUE-0010","CODOL-ISSUE-0041"}


def load_data():
    data = {}
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("_data_") and fn.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(HERE, fn))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for d in (mod.__dict__.values()):
            if isinstance(d, dict) and all(isinstance(v, dict) for v in d.values()):
                data.update(d)
    return data


def load_register():
    with open(REG, encoding="utf-8") as f:
        return {i["id"]: i for i in json.load(f)["issues"]}


def na(reason):
    return "`NOT_APPLICABLE` — %s" % reason


def render(iid, d, reg):
    L = []
    a = L.append
    a("# %s — %s\n" % (iid, d["title"]))
    a("> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`\n")
    a("---\n")

    # 1
    a("## 1. 问题精确定义\n")
    a(d["defect"] + "\n")

    # 2
    a("## 2. 历史首次发现过程\n")
    a("- **首次发现**：%s（`%s`）" % (d["first_seen"], d["first_seen_src"]))
    a("- **最近验证**：%s" % d["recent"])
    a("- **所属系统**：`%s`　**优先级**：%s　**登记状态**：`%s`　**严重度**：%s" % (
        d["system"], d["prio"], d["status"], d["severity"]))
    a("- **是否阻塞可玩战斗**：%s" % ("是" if d.get("blocks") else "否"))
    a("")

    # 3
    a("## 3. 全部相关历史实验\n")
    a("| 日期 | 实验/事件 | 结果 |")
    a("|---|---|---|")
    for row in d["history"]:
        a("| %s | %s | %s |" % row)
    a("")

    # 4
    a("## 4. 原始证据及 SHA-256\n")
    a("| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |")
    a("|---|---|---|---|---|---|")
    def norm3(t):
        t = tuple(t)
        return t + ("",) * (3 - len(t)) if len(t) < 3 else t[:3]

    n = 0
    for src in d["source"]:
        n += 1
        f, loc, note = norm3(src)
        a("| EV-%s-%02d | source | `%s` | %s | %s | — |" % (iid[-4:], n, f, loc, note or "见 §5"))
    for row in d["routes"]:
        n += 1
        f, loc, note = norm3(row)
        a("| EV-%s-%02d | location | `%s` | %s | %s | — |" % (iid[-4:], n, f, loc, note))
    a("")
    a("> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。")
    a("")

    # 5
    a("## 5. 当前源码位置\n")
    app = [s for s in d["source"] if s[0] != "—"]
    if app:
        a("| 文件 | 行 | 说明 |")
        a("|---|---|---|")
        for s in app:
            a("| `%s` | %s | %s |" % s)
    else:
        a(na("该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。"))
    a("")

    # 6
    a("## 6. 关键函数及调用关系\n")
    a("| 文件/地址 | 行/位置 | 作用 |")
    a("|---|---|---|")
    for r in d["routes"]:
        f, loc, note = norm3(r)
        a("| `%s` | %s | %s |" % (f, loc, note))
    a("")

    # 7
    cl = [s for s in d["source"] if s[0] == "—"]
    a("## 7. 客户端逆向证据\n")
    if d["system"] in ("client-re", "lobby", "protocol", "evidence-quality"):
        a("本 Issue（%s）涉及客户端逆向的部分见 §6；相关专项见 `06_CLIENT_REVERSE_ENGINEERING_GAPS.md`"
          " 中 %s 一节。" % (iid, d["system"]))
        if cl:
            a("\n证据载体：客户端二进制（3.19 / 1649370），非本仓库源码；具体函数/地址见 §6 表格的 %s 行。"
              % (d["routes"][0][0] if d["routes"] else "—"))
    else:
        a(na("该问题（%s，系统 `%s`）不涉及客户端逆向。" % (iid, d["system"])))
    a("")

    # 8
    a("## 8. 网络协议字段及字节布局\n")
    if d["system"] in ("protocol", "battle-network", "lobby", "battle-snapshot"):
        a("本 Issue 的协议字段与字节布局：见 §6 的 `%s`，以及 `05_PROTOCOL_GAPS.md` 中 %s 对应小节。"
          % (d["routes"][0][0] if d["routes"] else "—", d["system"]))
    else:
        a(na("该问题（%s，系统 `%s`）不涉及线上协议字段与字节布局。" % (iid, d["system"])))
    a("")

    # 9
    a("## 9. 完整数据流\n")
    a("```")
    a(d["flow"])
    a("```")
    a("")

    # 10
    a("## 10. 第一条未闭合调用边\n")
    a("**%s**" % d["first_open"])
    a("")

    # 11
    a("## 11. 已确认事实\n")
    for x in d["confirmed"]:
        a("- %s" % x)
    a("")

    # 12
    a("## 12. 尚未确认的假设\n")
    for x in d["unknown"]:
        a("- %s" % x)
    a("")

    # 13
    a("## 13. 已排除的假设\n")
    if d["excluded"]:
        for x in d["excluded"]:
            a("- %s" % x)
    else:
        a("(本 Issue 尚无已排除假设)")
    a("")

    # 14
    a("## 14. 历史修复尝试\n")
    if d["fix_attempts"]:
        a("| 时间 | 改动 | 结果 |")
        a("|---|---|---|")
        for row in d["fix_attempts"]:
            a("| %s | %s | %s |" % row)
    else:
        a("(无历史修复尝试)")
    a("")

    # 15
    a("## 15. 当前代码状态\n")
    a(d["code_state"] + "\n")

    # 16
    a("## 16. 最小复现条件\n")
    a(d["repro"] + "\n")

    # 17
    a("## 17. 最小验证实验\n")
    e = d["exp"]
    a("**实验 %s**" % e["id"])
    a("")
    a("| 项 | 内容 |")
    a("|---|---|")
    a("| 步骤 | %s |" % "<br>".join("%d. %s" % (i + 1, s) for i, s in enumerate(e["steps"])))
    a("| 通过判据 | %s |" % e.get("pass_", e.get("pass")))
    a("| 失败判据 | %s |" % e.get("fail_", e.get("fail")))
    a("| 成本 | %s |" % e["cost"])
    a("")

    # 18
    a("## 18. 条件式修复方案\n")
    a("**%s**" % d["fixA"])
    a("")
    a("**%s**" % d["fixB"])
    a("")

    # 19
    a("## 19. 修改影响分析\n")
    a(d["impact"] + "\n")

    # 20
    a("## 20. 可测量的验收标准\n")
    a("1. %s" % d["accept"])
    a("")

    # 21
    a("## 21. 回归测试方案\n")
    a(d["regress"] + "\n")

    # 22
    a("## 22. 修复准备度\n")
    a("**%s**\n" % d["readiness"])
    a("- **下一步**：%s" % d["next_step"])
    a("- **上游依赖**：%s" % (", ".join("`%s`" % x for x in d["deps"]) if d["deps"] else "无"))
    a("")
    a("---")
    return "\n".join(L)


def main():
    data = load_data()
    reg = load_register()
    os.makedirs(OUT, exist_ok=True)
    written = 0
    for iid, d in data.items():
        if iid not in reg:
            print("SKIP unknown id", iid, file=sys.stderr)
            continue
        if iid in HANDWRITTEN and os.path.isfile(os.path.join(OUT, iid + ".md")):
            continue  # keep hand-written 22-section dossier intact
        with open(os.path.join(OUT, iid + ".md"), "w", encoding="utf-8") as f:
            f.write(render(iid, d, reg))
        written += 1
    print("rendered %d dossiers (data entries: %d)" % (written, len(data)))


if __name__ == "__main__":
    main()
