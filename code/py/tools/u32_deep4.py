#!/usr/bin/env python3
"""0x08 深挖四：验证 0x6cc0 = 抓包机墙钟时间（+1 年偏移）；71/4 硬件指纹。"""
import collections
import datetime
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def run_dt(run):
    # ONCE_20261026_143143
    try:
        s = run.split("_", 1)[1]
        return datetime.datetime.strptime(s, "%Y%m%d_%H%M%S")
    except Exception:
        return None


print("=== 80/119 时间戳 vs run 名（UTC+8 解释）===")
diffs = []
for r in corpus:
    if (r["svc"], r["task"]) != (80, 119):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    ts = None
    for t, v in els:
        if t == 0x08 and isinstance(v, bytes) and len(v) == 4:
            iv = int.from_bytes(v, "little")
            if 0x6cc00000 <= iv <= 0x6cc0ffff:
                ts = iv
    rd = run_dt(r.get("run", ""))
    if ts and rd:
        ts_local = datetime.datetime.utcfromtimestamp(ts + 8 * 3600)
        delta = (ts_local - rd).total_seconds()
        diffs.append(delta)
        print("  run=%s  ts_local=%s  Δ=%+.0fs" % (r.get("run"), ts_local.strftime("%Y-%m-%d %H:%M:%S"), delta))
print("\n  Δ 统计: n=%d min=%.0f max=%.0f" % (len(diffs), min(diffs), max(diffs)))
print("  Δ 去掉 1 年(31536000s)后: min=%.0f max=%.0f" % (min(diffs) - 31536000, max(diffs) - 31536000))

print("\n=== 71/4 全样本（unicode_escape 输出）===")
seen = 0
for r in corpus:
    if (r["svc"], r["task"]) != (71, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    print("  --- len=%d run=%s ---" % (len(b), r.get("run")))
    for i, (t, v) in enumerate(els):
        if isinstance(v, bytes):
            esc = v.decode("latin1", "replace").encode("unicode_escape").decode()
            print("   #%02d 0x%02x len=%d hex=%s txt=%s" % (i, t, len(v), v.hex(), esc))
        else:
            print("   #%02d 0x%02x %r" % (i, t, v))
    seen += 1
    if seen >= 3:
        break

# 71/4 的 31902622 是否恒定 + 16B blob 是否恒定
print("\n=== 71/4 三个固定字段的全语料取值 ===")
c0 = collections.Counter(); c1 = collections.Counter(); c2 = collections.Counter(); c5 = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (71, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    try:
        c0[els[0][1].hex()] += 1
        c1[els[1][1].hex()] += 1
        c2[int.from_bytes(els[2][1], "little")] += 1
        c5[els[5][1].decode("latin1")] += 1
    except Exception:
        pass
print("  #0 blob16:", dict(c0))
print("  #1 blob16:", dict(c1))
print("  #2 u32   :", dict(c2))
print("  #5 str   :", dict(c5))
