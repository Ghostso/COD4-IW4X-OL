#!/usr/bin/env python3
"""第四轮: 纯丢弃 8 条(其信息已在 topic 文件 + 被合并行引用)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

DROP = [
    "- [★ 剧情卡",
    "- [★ 6/5 是读排队消息",
    "- [★ 登录绕过的边界",
    "- [★ dwRoom协议已逆向",
    "- [Demonware层与RTTI对象模型",
    "- [FAT分片帧真实布局",
    "- [★★★★★ 8/3档案上传",
    "- [★ 本build开发者接口清单",
]

lines = io.open(P, encoding="utf-8").read().split("\n")
kept, dropped = [], []
for ln in lines:
    if any(ln.startswith(d) for d in DROP):
        dropped.append(ln[:36])
        continue
    kept.append(ln)
out = "\n".join(kept)
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("丢弃 %d 条:" % len(dropped))
for d in dropped:
    print("   ", d)
print("新字节数 %d" % len(out.encode("utf-8")))
