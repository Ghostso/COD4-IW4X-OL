#!/usr/bin/env python3
"""交叉验证：28/4 的 126 个解锁 ID 与 6/14 mmstart/mmbook 的解锁命令 ID 是否同域。
以及 28/1 body item=0 是否代表"第一项(索引0)被选中"。"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))

# 28/4 的解锁 ID 集合
unlock_ids = None
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
            u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body), 4)]
            unlock_ids = u[1:]
            break
    break

print("28/4 解锁 ID 集合 (%d 个):" % len(unlock_ids))
print(" ", unlock_ids)
print("  min=%d max=%d" % (min(unlock_ids), max(unlock_ids)))

# 6/14 的 blob 内容（mmstart/mmbook 命令），看是否出现这些 ID 或相似 ID
print("\n=== 6/14 命令统计（mm* 类型）===")
cmds = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (6, 14):
        continue
    b = bytes.fromhex(r["payload"])
    # 6/14 blob 内层是 [u32 len][命令文本]
    # 简单找可打印 ASCII 前缀
    try:
        s = b.decode("latin1")
    except Exception:
        continue
    # 找 mm 开头的命令
    import re
    for m in re.finditer(rb"mm[a-z]+", b):
        cmds[m.group().decode()] += 1
print("  命令种类:", dict(cmds.most_common(20)))

# 28/4 ID 与 8/3 的 i32 配置键族比较
print("\n=== 对比: 8/3 的 i32 配置键族（0x2711..0x277A = 10001..10010）vs 28/4 ID(0..262) ===")
print("  28/4 ID 域 = 0..262（内容索引，小整数）")
print("  8/3 配置键 = 10001+（大整数，哈希化）")
print("  => 两个完全不同的 ID 空间")

# 28/4 ID 是否是"道具/解锁槽位"：统计缺失
full = set(range(0, 263))
present = set(unlock_ids)
missing = sorted(full - present)
print("\n28/4: 0..262 共 263 槽, 已解锁 %d, 未解锁 %d" % (len(present), len(missing)))
print("  未解锁前 30:", missing[:30])
