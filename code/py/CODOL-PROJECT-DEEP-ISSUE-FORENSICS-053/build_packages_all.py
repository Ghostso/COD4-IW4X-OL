#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate INVESTIGATION_PACKAGES/ and FIX_PACKAGES/ for P0+P1 issues
from the dossier data. Every package has the required sub-documents.
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
INV = os.path.join(HERE, "INVESTIGATION_PACKAGES")
FIX = os.path.join(HERE, "FIX_PACKAGES")


def load_data():
    data = {}
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("_data_") and fn.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(HERE, fn))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for d in mod.__dict__.values():
            if isinstance(d, dict) and d and all(isinstance(v, dict) for v in d.values()):
                data.update(d)
    return data


# P0 set already has hand-written dossiers+packages; only add P1 here.
def all_active_ids(data):
    import json
    reg = json.load(open(os.path.join(os.path.dirname(HERE),
        "CODOL-PROJECT-GLOBAL-UNRESOLVED-ISSUES-AUDIT", "MASTER_ISSUES.json"), encoding="utf-8"))["issues"]
    return [i["id"] for i in reg
            if i["priority"] in ("P0", "P1", "P2", "P3")]


def w(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    data = load_data()
    made_inv = made_fix = 0
    for iid in all_active_ids(data):
        d = data.get(iid)
        if not d or "exp" not in d:
            continue  # P0: hand-written package already exists
        root = FIX if d["readiness"] == "FIX_READY" else INV
        base = os.path.join(root, iid)
        head = "# %s — %s\n\n> fix_readiness = **%s**\n> 完整档案：[`../../ISSUES/%s.md`](../../ISSUES/%s.md)\n\n" % (
            iid, d["title"], d["readiness"], iid, iid)
        w(os.path.join(base, "README.md"), head + "## 下一步\n\n%s\n\n## 上游依赖\n\n%s\n" % (
            d["next_step"], ", ".join(d.get("deps") or []) or "无"))
        w(os.path.join(base, "EVIDENCE.md"),
          "# 证据\n\n| 文件 | 位置 | 说明 |\n|---|---|---|\n" +
          "\n".join("| `%s` | %s | %s |" % (t[0], t[1] if len(t) > 1 else "", t[2] if len(t) > 2 else "")
                    for t in list(d["source"]) + list(d["routes"])) + "\n")
        w(os.path.join(base, "ROOT_CAUSE.md"),
          "# 根因候选\n\n**第一条未闭合边**：%s\n\n## 已确认\n%s\n\n## 未确认\n%s\n" % (
              d["first_open"],
              "\n".join("- " + x for x in d["confirmed"]),
              "\n".join("- " + x for x in d["unknown"])))
        w(os.path.join(base, "TARGET_SOURCE.md"),
          "# 目标源码位置\n\n| 文件 | 行 | 说明 |\n|---|---|---|\n" +
          "\n".join("| `%s` | %s | %s |" % (t[0], t[1] if len(t) > 1 else "", t[2] if len(t) > 2 else "")
                    for t in d["source"]) + "\n")
        e = d["exp"]
        w(os.path.join(base, "TEST_PLAN.md"),
          "# 验证实验 %s\n\n## 步骤\n%s\n\n## 通过判据\n%s\n\n## 失败判据\n%s\n\n## 成本\n%s\n" % (
              e["id"], "\n".join("%d. %s" % (i + 1, s) for i, s in enumerate(e["steps"])),
              e.get("pass_", e.get("pass", "—")), e.get("fail_", e.get("fail", "—")), e["cost"]))
        w(os.path.join(base, "ACCEPTANCE.md"),
          "# 验收标准\n\n1. %s\n\n# 回归\n\n%s\n" % (d["accept"], d["regress"]))
        if d["readiness"] == "FIX_READY":
            made_fix += 1
            w(os.path.join(base, "PATCH_PLAN.md"),
              "# 修改计划\n\n**方案A**：%s\n\n**方案B**：%s\n\n## 影响\n\n%s\n" % (
                  d["fixA"], d["fixB"], d["impact"]))
            w(os.path.join(base, "ROLLBACK.md"),
              "# 回滚\n\n该问题位于可独立回退的位置。回滚方式：还原目标文件到修改前版本"
              "（源码目录 `CODOL_SERVER_319_20261021/src/` 下的单一文件），或"
              "在 kit 场景下用上一版 `lobby_server.py` 覆盖。\n\n"
              "修改前请记录目标文件的 SHA-256（见 `EVIDENCE_INDEX.json`）。\n")
        else:
            made_inv += 1
            w(os.path.join(base, "PATCH_PLAN.md"),
              "# 为什么没有补丁\n\n当前 fix_readiness = `%s`，尚不具备直接修复条件。\n"
              "必须先完成 `TEST_PLAN.md` 的实验，或先解决依赖：%s\n" % (
                  d["readiness"], ", ".join(d.get("deps") or []) or "无"))
    print("fix packages : %d" % made_fix)
    print("investigation: %d (P1, +7 hand-written P0)" % made_inv)


if __name__ == "__main__":
    main()
