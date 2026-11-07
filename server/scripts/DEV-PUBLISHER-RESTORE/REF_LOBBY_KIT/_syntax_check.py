# -*- coding: utf-8 -*-
"""语法检查几个关键脚本。"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
for f in ("lobby_server.py", "marketplace_store.py", "codol_crypto.py",
          "run_all.py", "nt10.py"):
    p = os.path.join(ROOT, f)
    if not os.path.exists(p):
        print("%-24s 缺失" % f)
        continue
    try:
        ast.parse(open(p, "r", encoding="utf-8").read())
        print("%-24s OK" % f)
    except SyntaxError as e:
        print("%-24s ★语法错误 %s" % (f, e))
sys.exit(0)
