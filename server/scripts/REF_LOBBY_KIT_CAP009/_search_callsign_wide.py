# -*- coding: utf-8 -*-
"""全项目搜索 callsign 相关处理代码(含第三方参考实现)。"""
import os
import re
import sys

PROJ = r"D:\BaiduNetdiskDownload\使命召唤OL"
PAT = re.compile(r"callsign|tryon|nameplate|dogtag|emblem", re.I)
SKIP = {"mem_linear", "mem_marketplace", "mem_callsign", "mem_sku",
        "__pycache__", ".git", "IIPSDownload", "main", "players",
        "components", "DirectX", "locales", "miles", "scripts",
        "WeGameLauncher", "TCLS", "TGuard", "Cross", "tqm"}
EXT = (".cs", ".cpp", ".h", ".hpp", ".py", ".md", ".txt")


def main():
    hits = []
    for base, dirs, files in os.walk(PROJ):
        dirs[:] = [d for d in dirs if d not in SKIP
                   and not d.startswith("mem_")]
        for fn in files:
            if not fn.lower().endswith(EXT):
                continue
            p = os.path.join(base, fn)
            try:
                if os.path.getsize(p) > 2 * 1024 * 1024:
                    continue
                txt = open(p, "r", encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if PAT.search(line):
                    rel = os.path.relpath(p, PROJ)
                    hits.append((rel, i, line.strip()[:130]))
    print("命中 %d 行" % len(hits))
    print()
    # 只看代码文件
    code = [h for h in hits if h[0].lower().endswith((".cs", ".cpp", ".h", ".hpp"))]
    print("代码文件命中 %d 行:" % len(code))
    for p, i, ln in code[:60]:
        print("%-58s %5d  %s" % (p, i, ln))
    print()
    print("其它文件前 40 行:")
    for p, i, ln in [h for h in hits if h not in code][:40]:
        print("%-58s %5d  %s" % (p, i, ln))
    return 0


if __name__ == "__main__":
    sys.exit(main())
