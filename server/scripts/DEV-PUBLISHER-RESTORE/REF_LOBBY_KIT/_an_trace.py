# -*- coding: utf-8 -*-
"""临时分析脚本：pred_trace.txt 的抖动 / 穿墙 / 落地定量分析（用完即删）。"""
import statistics as st

rows = []
for ln in open("pred_trace.txt", encoding="utf-8"):
    if ln.startswith("#"):
        continue
    p = ln.split()
    if len(p) < 7:
        continue
    try:
        rows.append(tuple(float(x) for x in p[:7]))
    except Exception:
        pass

n = len(rows)
if n < 10:
    print("样本太少: %d" % n)
    raise SystemExit

ts = [r[0] for r in rows]
zs = [r[3] for r in rows]
xs = [r[1] for r in rows]
ys = [r[2] for r in rows]
dt = [ts[i + 1] - ts[i] for i in range(n - 1)]
span = ts[-1] - ts[0]

print("样本=%d  时长=%.1fs  采样间隔: 中位=%.2fms 均值=%.2fms"
      % (n, span, 1000 * st.median(dt), 1000 * st.mean(dt)))

print("\n[z]  min=%.2f  max=%.2f  峰峰=%.2f  均值=%.3f  标准差=%.3f"
      % (min(zs), max(zs), max(zs) - min(zs), st.mean(zs), st.pstdev(zs)))

dz = [zs[i + 1] - zs[i] for i in range(n - 1)]
sig = [d for d in dz if abs(d) > 0.05]
flips = sum(1 for i in range(1, len(sig)) if sig[i] * sig[i - 1] < 0)
print("[z 抖动] |dz|>0.05 的步数=%d  符号翻转=%d  => 抖动率≈%.1f 次/秒  平均|dz|=%.3f"
      % (len(sig), flips, flips / span if span else 0,
         st.mean([abs(d) for d in sig]) if sig else 0))

# 静止段（x,y 基本不变）里的 z 幅度 —— 抖动最纯的度量
still = [i for i in range(1, n) if (xs[i] - xs[i - 1]) ** 2 + (ys[i] - ys[i - 1]) ** 2 < 0.01]
if len(still) > 20:
    sz = [zs[i] for i in still]
    print("[静止段] 样本=%d  z 峰峰=%.3f  标准差=%.4f"
          % (len(still), max(sz) - min(sz), st.pstdev(sz)))

# x/y 瞬时大跳（穿墙嫌疑）
big = [(ts[i], xs[i] - xs[i - 1], ys[i] - ys[i - 1])
       for i in range(1, n)
       if (xs[i] - xs[i - 1]) ** 2 + (ys[i] - ys[i - 1]) ** 2 > 30 * 30]
print("\n[x/y 单 tick 位移 >30]  次数=%d" % len(big))
for t, dx, dy in big[:10]:
    print("   t=%.2f  dx=%.1f dy=%.1f" % (t, dx, dy))

# 落地事件：vz 由 < -20 转 >= -1
land = [(ts[i], zs[i], rows[i - 1][6], rows[i][6])
        for i in range(1, n) if rows[i - 1][6] < -20 and rows[i][6] >= -1]
print("\n[落地事件 vz<-20 -> >=-1]  次数=%d" % len(land))
for t, z, vp, v in land[:10]:
    print("   t=%.2f  z=%.2f  vz: %.1f -> %.1f" % (t, z, vp, v))

# 最大单 tick z 下冲
worst = min(range(1, n), key=lambda i: dz[i - 1])
print("\n[最大单 tick z 下冲] t=%.2f  dz=%.3f  z=%.2f  vz_prev=%.1f"
      % (ts[worst], dz[worst - 1], zs[worst], rows[worst - 1][6]))
