# -*- coding: utf-8 -*-
"""搜索项目里所有与 Callsign(名片/徽章/称号) 相关的代码与数据。"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
PAT = re.compile(r"callsign|nameplate|badge|emblem|title", re.I)
SKIP_DIRS = {"mem_linear", "mem_marketplace", "mem_callsign", "mem_sku",
             "mkt_assets", "__pycache__", ".git", "backups",
             "backup_reverse_engineering", "工具"}


def main():
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith((".py", ".md", ".txt", ".json", ".csv")):
                continue
            p = os.path.join(base, fn)
            try:
                if os.path.getsize(p) > 4 * 1024 * 1024:
                    continue
                txt = open(p, "r", encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if PAT.search(line):
                    hits.append((os.path.relpath(p, ROOT), i, line.strip()[:150]))
    print("命中 %d 行" % len(hits))
    for p, i, ln in hits[:80]:
        print("%-42s %5d  %s" % (p, i, ln))
    return 0


if __name__ == "__main__":
    sys.exit(main())
