#!/usr/bin/env python3
"""追踪 IWff0100 分支的完整执行路径。
0x483df0 比对 IWff0100 -> 匹配则 jmp 0x483e2b
0x483e2b 之后做什么？
"""
import sys

sys.path.insert(0, "tools")
import subprocess

out = subprocess.run(["python", "-I", "tools/disasm_dump.py", "0x483e20", "200"],
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace").stdout
print(out)
