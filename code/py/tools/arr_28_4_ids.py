#!/usr/bin/env python3
"""28/4 的 127 个内容 ID 深度分析：分布、缺口、与 count=263 的关系。"""
IDS = [127, 0, 1, 2, 3, 9, 10, 12, 14, 18, 20, 21, 22, 23, 24, 27, 29, 31, 38, 75,
       76, 77, 79, 84, 85, 89, 94, 98, 102, 103, 106, 107, 117, 118, 119, 120, 121,
       124, 125, 126]
# 需要完整列表，重新从语料提取
import json
import sys
sys.path.insert(0, "tools")
import lobby_grammar_v5 as G

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        continue
    for t, v in els:
        if t == 0x6C:
            cnt, body = v
            IDS = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body), 4)]
            print("count 字段 = %d" % cnt)
            print("实际 ID 数 = %d" % len(IDS))
            break
    break

print("\n=== 127 个 ID 全列表 ===")
print(IDS)
print("\nmin=%d max=%d" % (min(IDS), max(IDS)))

# 排序检查
print("\n是否已排序:", IDS == sorted(IDS))
print("第一个 = %d, 之后:", IDS[1:15])

# 缺口分析
s = sorted(IDS[1:])  # 去掉第一个 127?
allrange = set(range(0, max(IDS) + 1))
missing = sorted(allrange - set(IDS))
print("\n0..%d 中缺失的 ID 数 = %d" % (max(IDS), len(missing)))
print("缺失的前 40:", missing[:40])

# 差值分布
print("\n相邻差值分布:")
import collections
d = collections.Counter(IDS[i+1] - IDS[i] for i in range(len(IDS)-1))
for k, n in sorted(d.items()):
    print("  Δ=%d x%d" % (k, n))

# 如果第一个 127 是"数量/版本"，剩下 126 个 ID
print("\n若首个 127 是头部(非 ID)，则 ID 数=%d, max=%d" % (len(IDS)-1, max(IDS[1:])))

# 0..262 里 ID 的密度
print("\nID 覆盖 0..262 的密度: %d/263 = %.1f%%" % (len([x for x in IDS if x <= 262]), 100.0*len([x for x in IDS if x <= 262])/263))
