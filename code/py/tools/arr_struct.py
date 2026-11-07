#!/usr/bin/env python3
"""0x6c 结构精确验证：bytelen == 4*len(body_u32)? tail 语义?
28/1 = 任务参数：body=选中索引, tail=可选总数?
28/4 = ContentUnlock2：body=已解锁内容ID, tail=总内容数?"""
import collections
import json
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))


def get_6c(r):
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    if not good:
        return None
    out = []
    for t, v in els:
        if t == 0x6C:
            cnt, body = v
            u = [int.from_bytes(body[j:j+4], "little") for j in range(0, len(body) - len(body) % 4, 4)]
            out.append((len(body), u, cnt))
    return out


# 1) bytelen 与 body u32 数关系（全 0x6c）
print("=== bytelen vs 4*len(body_u32) 一致性 ===")
bad = 0
tot = 0
for r in corpus:
    for item in (get_6c(r) or []):
        bl, u, cnt = item
        tot += 1
        if bl != 4 * len(u):
            bad += 1
print("总 0x6c = %d, 不一致 = %d (说明 body 长度总是 4 的倍数)" % (tot, bad))

# 2) 28/1 的 (body_u32, tail) 组合 + run 顺序
print("\n=== 28/1 (body_u32, tail) 组合 ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (28, 1):
        continue
    for bl, u, cnt in (get_6c(r) or []):
        c[(tuple(u), cnt)] += 1
for (u, cnt), n in c.most_common():
    print("  body=%-18s tail=%-4d  x%d" % (list(u), cnt, n))

# 3) 28/4 body[0] 与 tail 关系
print("\n=== 28/4 body 首元素 与 tail ===")
c = collections.Counter()
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    for bl, u, cnt in (get_6c(r) or []):
        c[(len(u), u[0] if u else None, cnt)] += 1
for k, n in c.most_common():
    print("  n_u32=%d body[0]=%s tail=%d x%d" % (k[0], k[1], k[2], n))

# 4) 28/4 若 body[0] 是元素数：body[1:] 是否 = 数据
print("\n=== 28/4 假设 body[0]=N(元素数) 检验 ===")
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    for bl, u, cnt in (get_6c(r) or []):
        print("  body[0]=%d  len(body)=%d  body[1:]长度=%d  tail=%d" %
              (u[0], len(u), len(u)-1, cnt))
        print("  -> body[0]==len(body)? %s ; body[0]==len(body)-1? %s" %
              (u[0] == len(u), u[0] == len(u)-1))
        break
    break

# 5) 28/1 的 N 与 tail：若 body=索引, tail=总数，检查 body 值是否 < tail
print("\n=== 28/1 body 值是否 < tail（索引<总数）===")
viol = 0
ok = 0
for r in corpus:
    if (r["svc"], r["task"]) != (28, 1):
        continue
    for bl, u, cnt in (get_6c(r) or []):
        if not u:
            continue
        if all(x < cnt for x in u):
            ok += 1
        else:
            viol += 1
            if viol <= 5:
                print("  违反: body=%s tail=%d" % (u, cnt))
print("  body全<tail: %d, 违反: %d" % (ok, viol))
