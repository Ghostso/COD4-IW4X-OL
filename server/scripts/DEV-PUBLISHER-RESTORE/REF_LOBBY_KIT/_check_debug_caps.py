# -*- coding: utf-8 -*-
"""检查现有的运行时挂钩能力: nt10.py 支持哪些 hook 点。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NT10 = os.path.join(ROOT, "nt10.py")


def main():
    if not os.path.exists(NT10):
        print("缺 nt10.py")
        return 1
    txt = open(NT10, "r", encoding="utf-8", errors="replace").read()
    lines = txt.splitlines()
    print("nt10.py: %d 行" % len(lines))
    print()
    # 找 hook / 开关 / 扫描点
    pats = {
        "hook 点": re.compile(r"HOOK|hook_|SetHook|安装.*钩子|挂钩"),
        "开关文件": re.compile(r"\.on['\"]|FLAG\s*=|flag"),
        "扫描线程": re.compile(r"threading\.Thread"),
        "dll 基址": re.compile(r"base|BaseDll|module"),
    }
    for name, pat in pats.items():
        idx = [i for i, l in enumerate(lines) if pat.search(l)]
        print("== %s: %d 处 ==" % (name, len(idx)))
        for i in idx[:18]:
            print("%5d| %s" % (i + 1, lines[i].strip()[:130]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
