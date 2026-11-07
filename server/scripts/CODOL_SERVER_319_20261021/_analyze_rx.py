# -*- coding: utf-8 -*-
"""分析战斗服 RX 日志：统计包类型、时序、是否有数据帧。"""
import re
from collections import Counter, OrderedDict
from pathlib import Path

p = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\CHAIN_UNIFIED_20261103\run_codol_001\runs\ONCE_20261105_153310\kit\_battle_out.txt")
lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
print("总行数:", len(lines))

rx = []
for ln in lines:
    m = re.match(r"\[battle\] RX (\d+)B FULL ([0-9A-F]+)", ln)
    if m:
        rx.append((int(m.group(1)), m.group(2)))
    elif "RX_DROP" in ln:
        rx.append((-1, ln.strip()))

print("RX 包总数:", len(rx))
sizes = Counter(n for n, _ in rx)
print("按长度:", dict(sorted(sizes.items())))

# 输出客户端发的前几个不同长度的包
print()
print("=== 各长度样例（首个） ===")
seen = {}
for n, h in rx:
    if n not in seen:
        seen[n] = h
for n in sorted(seen, key=lambda x: (x < 0, x)):
    h = seen[n]
    print(f"  len={n}: {h[:150]}")

# 按序列看状态机流转
print()
print("=== 前 40 个 RX 事件顺序 ===")
for i, (n, h) in enumerate(rx[:40]):
    print(f"  #{i:3d} len={n:<5} {h[:90]}")

# 找有没有非握手长度（>219 或明显是数据帧）
print()
print("=== 非 29/16/219 的包 ===")
for n, h in rx:
    if n not in (29, 16, 219, -1):
        print(f"  len={n}: {h[:200]}")
