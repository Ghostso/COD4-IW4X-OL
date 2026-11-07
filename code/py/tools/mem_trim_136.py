#!/usr/bin/env python3
"""第三轮: 丢掉 8 条低价值条目(内容均已在各自 topic 文件 + 合并行里被引用)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

DROP = [
    "- [mp_firingrange clipmap",
    "- [两个热分发槽是 _strdup",
    "- [日志可读性分类",
    "- [TCLS 启动门禁",
    "- [TCLS 共享内存握手",
    "- [启动链真正的终点",
    "- [登录绕过的边界",
    "- [grep 目录级搜索跳过二进制",
]

lines = io.open(P, encoding="utf-8").read().split("\n")
kept, dropped = [], []
for ln in lines:
    if any(ln.startswith(d) for d in DROP):
        dropped.append(ln[:40])
        continue
    kept.append(ln)
out = "\n".join(kept)
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("丢弃 %d 条:" % len(dropped))
for d in dropped:
    print("   ", d)
print("新字节数 %d" % len(out.encode("utf-8")))
